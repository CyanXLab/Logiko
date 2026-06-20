#!/usr/bin/env python3
"""
SFT (Supervised Fine-Tuning) for Logiko
=========================================
Loads a pretrained checkpoint, fine-tunes on Q&A pairs.

Format per example:
    <bos>Q: <question>\nA: <answer><eos>

Loss is computed ONLY on the answer tokens (prompt tokens are masked out).
"""
import os
import sys
import json
import time
import math
import argparse
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tokenizer import BPETokenizer, BOS_ID, EOS_ID, PAD_ID
from model import LogikoLM, ModelConfig, save_model, load_model


class SFTDataset(Dataset):
    """SFT 数据集：每个样本是 (prompt_ids, answer_ids)
    构造为 (input_ids, labels) 其中 labels 在 prompt 部分 = -100（忽略），
    answer 部分 = answer token ids + EOS。
    """

    def __init__(self, examples: list, tokenizer: BPETokenizer, max_len: int = 256):
        self.examples = examples
        self.tok = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        ex = self.examples[idx]
        # 构造 prompt: "<question>\n"  (no Q: A: prefix; let model learn directly)
        prompt = f"{ex['question']}\n"
        # 构造 completion: "<answer>"
        completion = ex["answer"]
        # 编码（不加 BOS，因为后面要拼接）
        prompt_ids = self.tok.encode(prompt, add_bos=False, add_eos=False)
        completion_ids = self.tok.encode(completion, add_bos=False, add_eos=False)
        completion_ids = completion_ids + [EOS_ID]

        # 拼接: <bos> prompt + completion
        full_ids = [BOS_ID] + prompt_ids + completion_ids
        # 截断
        if len(full_ids) > self.max_len + 1:
            full_ids = full_ids[:self.max_len + 1]

        # input_ids = full_ids[:-1] (the context)
        # labels[i] = full_ids[i+1] (the next-token target)
        input_ids = full_ids[:-1]
        labels = full_ids[1:]

        # mask prompt 部分：prompt 长度（含 BOS） = 1 + len(prompt_ids)
        prompt_len = 1 + len(prompt_ids)
        for i in range(min(prompt_len, len(labels))):
            labels[i] = -100

        # padding
        pad_len = self.max_len - len(input_ids)
        if pad_len > 0:
            input_ids = input_ids + [PAD_ID] * pad_len
            labels = labels + [-100] * pad_len

        # 截断到 max_len
        input_ids = input_ids[:self.max_len]
        labels = labels[:self.max_len]

        return (
            torch.tensor(input_ids, dtype=torch.long),
            torch.tensor(labels, dtype=torch.long),
        )


def load_sft_data(path: str):
    examples = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ex = json.loads(line)
            examples.append(ex)
    return examples


def get_lr(step, warmup, max_steps, max_lr, min_lr):
    if step < warmup:
        return max_lr * (step + 1) / warmup
    if step >= max_steps:
        return min_lr
    progress = (step - warmup) / max(1, max_steps - warmup)
    coeff = 0.5 * (1.0 + math.cos(math.pi * progress))
    return min_lr + coeff * (max_lr - min_lr)


def sft_train(args):
    device = torch.device(args.device)
    print(f"Device: {device}")

    # 1. Tokenizer
    tok = BPETokenizer.load("/home/z/my-project/logiko/tokenizer.json")
    print(f"Tokenizer vocab size: {len(tok.vocab)}")

    # 2. SFT 数据
    examples = load_sft_data(args.sft_data)
    print(f"Loaded {len(examples)} SFT examples")
    # 切分 train/val
    random.shuffle(examples)
    n_val = min(200, len(examples) // 20)
    val_examples = examples[:n_val]
    train_examples = examples[n_val:]
    print(f"Train: {len(train_examples)}, Val: {len(val_examples)}")

    train_dataset = SFTDataset(train_examples, tok, max_len=args.max_len)
    val_dataset = SFTDataset(val_examples, tok, max_len=args.max_len)

    train_loader = DataLoader(
        train_dataset, batch_size=args.batch_size, shuffle=True,
        num_workers=0, drop_last=True,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0,
    )

    # 3. 加载预训练模型
    print(f"Loading pretrained model from {args.pretrained}...")
    model, extra = load_model(args.pretrained, map_location=device)
    model.to(device)
    print(f"Model loaded. Pretrained step={extra.get('step')}, loss={extra.get('loss')}")
    print(f"Params: {model.num_parameters():,}")

    # 4. 优化器
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.max_lr,
        betas=(0.9, 0.95),
        eps=1e-8,
        weight_decay=args.weight_decay,
    )

    # 5. 训练循环
    grad_accum = args.grad_accum
    update_step = 0
    t0 = time.time()
    running_loss = 0.0
    running_count = 0
    best_val_loss = float("inf")

    print(f"\nStarting SFT: {args.max_steps} steps, batch={args.batch_size}, grad_accum={grad_accum}")
    print()

    data_iter = iter(train_loader)
    model.train()

    while update_step < args.max_steps:
        optimizer.zero_grad(set_to_none=True)
        total_loss = 0.0
        for _ in range(grad_accum):
            try:
                x, y = next(data_iter)
            except StopIteration:
                data_iter = iter(train_loader)
                x, y = next(data_iter)
            x = x.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)

            _, loss = model(x, y)
            loss = loss / grad_accum
            loss.backward()
            total_loss += loss.item()

        if args.max_grad_norm > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)

        lr = get_lr(update_step, args.warmup, args.max_steps, args.max_lr, args.min_lr)
        for pg in optimizer.param_groups:
            pg["lr"] = lr
        optimizer.step()

        running_loss += total_loss
        running_count += 1
        update_step += 1

        if update_step % args.log_every == 0:
            avg_loss = running_loss / running_count
            running_loss = 0.0
            running_count = 0
            elapsed = time.time() - t0
            sps = update_step / elapsed
            ppl = math.exp(min(avg_loss, 20.0))
            print(
                f"step {update_step:5d}/{args.max_steps} | loss {avg_loss:.4f} | ppl {ppl:.2f} | lr {lr:.2e} | "
                f"{sps:.2f} step/s | elapsed {elapsed:.0f}s"
            )

        # 验证
        if update_step % args.eval_every == 0:
            model.eval()
            val_loss = 0.0
            val_count = 0
            with torch.no_grad():
                for x, y in val_loader:
                    x = x.to(device)
                    y = y.to(device)
                    _, loss = model(x, y)
                    val_loss += loss.item()
                    val_count += 1
            avg_val_loss = val_loss / max(1, val_count)
            avg_val_ppl = math.exp(min(avg_val_loss, 20.0))
            print(f"  >> val_loss={avg_val_loss:.4f}, val_ppl={avg_val_ppl:.2f}")
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                ckpt = os.path.join(args.ckpt_dir, "logiko_sft_best.pt")
                save_model(model, ckpt, extra={
                    "step": update_step,
                    "train_loss": avg_loss,
                    "val_loss": avg_val_loss,
                    "stage": "sft",
                })
            model.train()

        if update_step % args.save_every == 0:
            ckpt = os.path.join(args.ckpt_dir, f"logiko_sft_step{update_step}.pt")
            save_model(model, ckpt, extra={"step": update_step, "loss": avg_loss, "stage": "sft"})

    # 保存最终
    final = os.path.join(args.ckpt_dir, "logiko_sft_final.pt")
    save_model(model, final, extra={"step": update_step, "loss": avg_loss, "stage": "sft"})
    print(f"\nSFT done. Final: {final}")
    print(f"Total time: {time.time()-t0:.1f}s, best val_loss: {best_val_loss:.4f}")


import random

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--pretrained", default="/home/z/my-project/logiko/logiko_final.pt")
    p.add_argument("--sft_data", default="/home/z/my-project/logiko/sft_data.jsonl")
    p.add_argument("--ckpt_dir", default="/home/z/my-project/logiko")
    p.add_argument("--device", default="cpu")
    p.add_argument("--max_len", type=int, default=192)
    p.add_argument("--batch_size", type=int, default=8)
    p.add_argument("--grad_accum", type=int, default=2)
    p.add_argument("--max_steps", type=int, default=2000)
    p.add_argument("--warmup", type=int, default=50)
    p.add_argument("--max_lr", type=float, default=2e-4)
    p.add_argument("--min_lr", type=float, default=2e-5)
    p.add_argument("--weight_decay", type=float, default=0.01)
    p.add_argument("--max_grad_norm", type=float, default=1.0)
    p.add_argument("--log_every", type=int, default=20)
    p.add_argument("--eval_every", type=int, default=200)
    p.add_argument("--save_every", type=int, default=500)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    os.makedirs(args.ckpt_dir, exist_ok=True)
    sft_train(args)
