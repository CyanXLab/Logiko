#!/usr/bin/env python3
"""
Logiko Pretraining Script
=========================
Standard causal LM pretraining:
  - AdamW optimizer (betas=(0.9, 0.95))
  - Cosine learning rate schedule with warmup
  - Gradient accumulation
  - Mixed precision (bfloat16 supported, falls back to fp32)
  - Periodic checkpoint saving
  - Tokenized corpus cached to disk for fast iteration
"""
import os
import sys
import time
import math
import json
import argparse
from typing import List

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

# 让 Python 能找到我们的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tokenizer import BPETokenizer, BOS_ID, EOS_ID, PAD_ID
from model import LogikoLM, ModelConfig, save_model, load_model


# =========================================================================
# Dataset
# =========================================================================

class TokenDataset(Dataset):
    """从一维 token 数组生成 (input, target) 对，每个样本长度 = seq_len + 1"""

    def __init__(self, tokens: List[int], seq_len: int):
        self.tokens = tokens
        self.seq_len = seq_len
        self.n_samples = max(0, len(tokens) - seq_len - 1)

    def __len__(self):
        return self.n_samples

    def __getitem__(self, idx):
        chunk = self.tokens[idx: idx + self.seq_len + 1]
        x = torch.tensor(chunk[:-1], dtype=torch.long)
        y = torch.tensor(chunk[1:], dtype=torch.long)
        return x, y


def load_and_tokenize(corpus_path: str, tokenizer: BPETokenizer, cache_path: str) -> List[int]:
    """加载语料并分词，缓存到磁盘"""
    if os.path.exists(cache_path):
        print(f"Loading cached tokens from {cache_path}")
        return torch.load(cache_path, weights_only=False)
    print(f"Tokenizing {corpus_path}...")
    with open(corpus_path, "r", encoding="utf-8") as f:
        text = f.read()
    # 全文一次性分词（不加 BOS，不加 EOS；用 </w>/\n 隐式标记）
    tokens = tokenizer.encode(text, add_bos=False, add_eos=False)
    # 每隔一段插入 EOS 作为文档边界
    # 简化：保留原样
    print(f"Tokenized: {len(tokens)} tokens")
    torch.save(tokens, cache_path)
    return tokens


# =========================================================================
# LR schedule
# =========================================================================

def get_lr(step: int, warmup: int, max_steps: int, max_lr: float, min_lr: float) -> float:
    if step < warmup:
        return max_lr * (step + 1) / warmup
    if step >= max_steps:
        return min_lr
    progress = (step - warmup) / max(1, max_steps - warmup)
    coeff = 0.5 * (1.0 + math.cos(math.pi * progress))
    return min_lr + coeff * (max_lr - min_lr)


# =========================================================================
# Train loop
# =========================================================================

def train(args):
    device = torch.device(args.device)
    print(f"Device: {device}")

    # 1. Tokenizer
    tok_path = "/home/z/my-project/logiko/tokenizer.json"
    tokenizer = BPETokenizer.load(tok_path)
    print(f"Tokenizer loaded. Vocab size: {len(tokenizer.vocab)}")

    # 2. 数据
    cache = "/home/z/my-project/logiko/tokens.pt"
    tokens = load_and_tokenize(args.corpus, tokenizer, cache)
    dataset = TokenDataset(tokens, args.seq_len)
    print(f"Dataset: {len(dataset)} samples")

    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=(device.type == "cuda"),
        drop_last=True,
    )

    # 3. 模型
    cfg = ModelConfig(
        vocab_size=len(tokenizer.vocab),
        d_model=args.d_model,
        n_heads=args.n_heads,
        n_layers=args.n_layers,
        d_ff=args.d_ff,
        max_seq_len=args.seq_len,
        dropout=0.0,
    )
    model = LogikoLM(cfg).to(device)
    n_params = model.num_parameters()
    print(f"Model: {n_params:,} parameters ({n_params/1e6:.2f}M)")

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
    total_micro_steps = args.max_steps * grad_accum
    micro_step = 0
    update_step = 0
    t0 = time.time()

    # 启用 AMP（CPU 用 bf16 仅在 AVX512_BF16 支持时，否则 fp32）
    use_amp = (device.type == "cuda") and args.amp
    amp_dtype = torch.bfloat16
    scaler = None

    model.train()
    running_loss = 0.0
    running_count = 0

    print(f"\nStarting training: {args.max_steps} optimizer steps, {grad_accum} grad-accum, batch_size={args.batch_size}")
    print(f"  Total tokens/step: {args.batch_size * args.seq_len * grad_accum:,}")
    print(f"  Effective batch tokens seen: {args.batch_size * args.seq_len * grad_accum * args.max_steps:,}")
    print()

    data_iter = iter(loader)
    while update_step < args.max_steps:
        # 累积梯度
        optimizer.zero_grad(set_to_none=True)
        total_loss = 0.0
        for _ in range(grad_accum):
            try:
                x, y = next(data_iter)
            except StopIteration:
                data_iter = iter(loader)
                x, y = next(data_iter)
            x = x.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)

            if use_amp:
                with torch.amp.autocast(device_type=device.type, dtype=amp_dtype):
                    _, loss = model(x, y)
                loss = loss / grad_accum
            else:
                _, loss = model(x, y)
                loss = loss / grad_accum

            loss.backward()
            total_loss += loss.item()
            micro_step += 1

        # 梯度裁剪
        if args.max_grad_norm > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)

        # 调整 LR
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
            steps_per_sec = update_step / elapsed
            ppl = math.exp(min(avg_loss, 20.0))
            tok_per_sec = steps_per_sec * args.batch_size * args.seq_len * grad_accum
            print(
                f"step {update_step:5d}/{args.max_steps} | loss {avg_loss:.4f} | ppl {ppl:.2f} | lr {lr:.2e} | "
                f"{steps_per_sec:.2f} step/s | {tok_per_sec:,.0f} tok/s | elapsed {elapsed:.0f}s"
            )

        if update_step % args.save_every == 0:
            ckpt_path = os.path.join(args.ckpt_dir, f"logiko_step{update_step}.pt")
            save_model(model, ckpt_path, extra={"step": update_step, "loss": avg_loss})

    # 保存最终模型
    final_path = os.path.join(args.ckpt_dir, "logiko_final.pt")
    save_model(model, final_path, extra={"step": update_step, "loss": avg_loss})
    print(f"\nTraining done. Final model: {final_path}")
    print(f"Total time: {time.time() - t0:.1f}s")


# =========================================================================
# CLI
# =========================================================================

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--corpus", default="/home/z/my-project/download/logiko_corpus.txt")
    p.add_argument("--ckpt_dir", default="/home/z/my-project/logiko")
    p.add_argument("--device", default="cpu")
    p.add_argument("--seq_len", type=int, default=256)
    # 模型尺寸（默认小模型 ~6M 参数，适合 CPU 训练）
    p.add_argument("--d_model", type=int, default=256)
    p.add_argument("--n_heads", type=int, default=8)
    p.add_argument("--n_layers", type=int, default=6)
    p.add_argument("--d_ff", type=int, default=1024)
    # 训练超参
    p.add_argument("--batch_size", type=int, default=32)
    p.add_argument("--grad_accum", type=int, default=4)
    p.add_argument("--max_steps", type=int, default=500)
    p.add_argument("--warmup", type=int, default=20)
    p.add_argument("--max_lr", type=float, default=3e-4)
    p.add_argument("--min_lr", type=float, default=3e-5)
    p.add_argument("--weight_decay", type=float, default=0.1)
    p.add_argument("--max_grad_norm", type=float, default=1.0)
    p.add_argument("--amp", action="store_true")
    p.add_argument("--num_workers", type=int, default=0)
    p.add_argument("--log_every", type=int, default=10)
    p.add_argument("--save_every", type=int, default=100)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    os.makedirs(args.ckpt_dir, exist_ok=True)
    train(args)
