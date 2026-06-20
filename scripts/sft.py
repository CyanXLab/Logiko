#!/usr/bin/env python3
"""
SFT v2 (Logiko v2.0) — Multi-turn Support
==========================================
Supports multi-turn conversations:
  - Each example has 1+ turns of (Q, A) pairs
  - Format: <bos>Q: <q1>\nA: <a1>\nQ: <q2>\nA: <a2>...<eos>
  - Loss computed ONLY on A parts (Q parts masked with -100)
  - Sliding window: if total length > max_len, truncate from start (keep latest turns)

Improvements over v1:
  - Multi-turn context support
  - Answer-only loss masking (per-turn)
  - Better padding
  - Validation split with multi-turn
"""
import os
import sys
import json
import time
import math
import argparse
import random
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tokenizer import BPETokenizer, BOS_ID, EOS_ID, PAD_ID
from model import LogikoLM, ModelConfig, save_model, load_model


class SFTDataset(Dataset):
    """Multi-turn SFT dataset.

    Each example: list of (question, answer) turns.
    Tokenize as: <bos> Q1 \n A1 <eos> \n Q2 \n A2 <eos> ... 
    Actually we use: <bos> "Q: q1\nA: a1\nQ: q2\nA: a2" <eos>
    
    Loss is computed on tokens INSIDE "A: ..." segments (everything after "A: " until next "\nQ: " or EOS).
    """

    def __init__(self, examples: list, tokenizer: BPETokenizer, max_len: int = 256):
        self.examples = examples
        self.tok = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.examples)

    def _encode_turns(self, turns):
        """Encode multi-turn conversation into (input_ids, labels).
        
        Returns:
            input_ids: list[int], length <= max_len
            labels: list[int], same length, -100 where loss should be ignored
        """
        full_ids = [BOS_ID]
        labels = [-100]  # BOS is never a target

        for turn_idx, (q, a) in enumerate(turns):
            # Encode Q part
            q_text = f"Q: {q}\nA: "
            q_ids = self.tok.encode(q_text, add_bos=False, add_eos=False)
            full_ids.extend(q_ids)
            labels.extend([-100] * len(q_ids))  # mask Q

            # Encode A part (include EOS at end of last turn, or \n for non-last)
            if turn_idx < len(turns) - 1:
                a_text = a + "\n"
            else:
                a_text = a
            a_ids = self.tok.encode(a_text, add_bos=False, add_eos=False)
            full_ids.extend(a_ids)
            labels.extend(a_ids)  # train on A

            # For last turn, append EOS
            if turn_idx == len(turns) - 1:
                full_ids.append(EOS_ID)
                labels.append(EOS_ID)

        # Truncate from start if too long (keep latest turns)
        if len(full_ids) > self.max_len:
            # Find a safe truncation point: don't cut in the middle of an A segment
            # Simple approach: just truncate from start, but try to start at a Q: boundary
            cut = len(full_ids) - self.max_len
            # Find next Q: or A: boundary after cut
            # For simplicity, just hard-truncate
            full_ids = full_ids[cut:]
            labels = labels[cut:]
            # Ensure first non-masked label aligns (set first few labels to -100 if needed)
            # Set labels at the start to -100 until we're sure we're in an A segment
            # Simple: set first 5 labels to -100 to avoid mid-word issues
            for i in range(min(5, len(labels))):
                labels[i] = -100

        return full_ids, labels

    def __getitem__(self, idx):
        ex = self.examples[idx]
        turns = ex["turns"]
        full_ids, labels = self._encode_turns(turns)

        # Convert to next-token prediction format
        # input_ids = full_ids[:-1], targets = full_ids[1:] shifted
        # But our labels are already aligned: labels[i] is target for input_ids[i] predicting input_ids[i+1]
        # Wait, let me re-think:
        # In standard LM: logits[i] predicts token[i+1]
        # So if we have full_ids = [t0, t1, t2, ...], we feed input = [t0, t1, ...] and target = [t1, t2, ...]
        # If labels[i] should be t[i+1], then we set:
        #   input_ids = full_ids[:-1]
        #   labels[i] = full_ids[i+1] if i+1 is in an A segment, else -100

        # Re-do: build input_ids and labels in shifted format
        input_ids = full_ids[:-1]
        target_ids = full_ids[1:]
        # The label for position i is target_ids[i] if it's part of an A segment
        # In our original labels, labels[j] is the label for full_ids[j]
        # But for next-token prediction, we want: input_ids[i] = full_ids[i], label = full_ids[i+1]
        # So we want: label[i] = (label of full_ids[i+1] in original) = original_labels[i+1]
        shifted_labels = labels[1:]  # length = len(input_ids)
        # Mask: only train where shifted_labels != -100
        # Also pad/truncate to max_len
        assert len(input_ids) == len(shifted_labels)

        # Truncate to max_len
        input_ids = input_ids[:self.max_len]
        shifted_labels = shifted_labels[:self.max_len]

        # Pad
        pad_len = self.max_len - len(input_ids)
        if pad_len > 0:
            input_ids = input_ids + [PAD_ID] * pad_len
            shifted_labels = shifted_labels + [-100] * pad_len

        return (
            torch.tensor(input_ids, dtype=torch.long),
            torch.tensor(shifted_labels, dtype=torch.long),
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

    tok = BPETokenizer.load("/home/z/my-project/logiko/tokenizer.json")
    print(f"Tokenizer vocab size: {len(tok.vocab)}")

    examples = load_sft_data(args.sft_data)
    print(f"Loaded {len(examples)} SFT examples")
    random.seed(42)
    random.shuffle(examples)
    n_val = min(200, len(examples) // 20)
    val_examples = examples[:n_val]
    train_examples = examples[n_val:]
    n_multi_train = sum(1 for ex in train_examples if len(ex["turns"]) > 1)
    print(f"Train: {len(train_examples)} ({n_multi_train} multi-turn), Val: {len(val_examples)}")

    train_dataset = SFTDataset(train_examples, tok, max_len=args.max_len)
    val_dataset = SFTDataset(val_examples, tok, max_len=args.max_len)

    train_loader = DataLoader(
        train_dataset, batch_size=args.batch_size, shuffle=True,
        num_workers=0, drop_last=True,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0,
    )

    print(f"Loading pretrained model from {args.pretrained}...")
    model, extra = load_model(args.pretrained, map_location=device)
    model.to(device)
    print(f"Model loaded. Pretrained step={extra.get('step')}, loss={extra.get('loss')}")
    print(f"Params: {model.num_parameters():,}")
    print(f"Model max_seq_len: {model.cfg.max_seq_len} (SFT max_len: {args.max_len})")
    assert args.max_len <= model.cfg.max_seq_len, "SFT max_len must be <= model max_seq_len"

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.max_lr,
        betas=(0.9, 0.95),
        eps=1e-8,
        weight_decay=args.weight_decay,
    )

    grad_accum = args.grad_accum
    update_step = 0
    t0 = time.time()
    running_loss = 0.0
    running_count = 0
    best_val_loss = float("inf")

    print(f"\nStarting SFT v2: {args.max_steps} steps, batch={args.batch_size}, grad_accum={grad_accum}")
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
                    "stage": "sft_v2",
                })
            model.train()

        if update_step % args.save_every == 0:
            ckpt = os.path.join(args.ckpt_dir, f"logiko_sft_step{update_step}.pt")
            save_model(model, ckpt, extra={"step": update_step, "loss": avg_loss, "stage": "sft_v2"})

    final = os.path.join(args.ckpt_dir, "logiko_sft_final.pt")
    save_model(model, final, extra={"step": update_step, "loss": avg_loss, "stage": "sft_v2"})
    print(f"\nSFT done. Final: {final}")
    print(f"Total time: {time.time()-t0:.1f}s, best val_loss: {best_val_loss:.4f}")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--pretrained", default="/home/z/my-project/logiko/logiko_final.pt")
    p.add_argument("--sft_data", default="/home/z/my-project/logiko/sft_data.jsonl")
    p.add_argument("--ckpt_dir", default="/home/z/my-project/logiko")
    p.add_argument("--device", default="cpu")
    p.add_argument("--max_len", type=int, default=192)
    p.add_argument("--batch_size", type=int, default=8)
    p.add_argument("--grad_accum", type=int, default=2)
    p.add_argument("--max_steps", type=int, default=1500)
    p.add_argument("--warmup", type=int, default=50)
    p.add_argument("--max_lr", type=float, default=1e-4)
    p.add_argument("--min_lr", type=float, default=1e-5)
    p.add_argument("--weight_decay", type=float, default=0.01)
    p.add_argument("--max_grad_norm", type=float, default=1.0)
    p.add_argument("--log_every", type=int, default=50)
    p.add_argument("--eval_every", type=int, default=200)
    p.add_argument("--save_every", type=int, default=500)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    os.makedirs(args.ckpt_dir, exist_ok=True)
    sft_train(args)
