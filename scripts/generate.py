#!/usr/bin/env python3
"""
Logiko Text Generation v2
==========================
Improvements:
  - Repetition penalty (default 1.2)
  - Better top-k / top-p sampling
  - EOS-aware stopping
  - Optional BOS prompt support
  - Optional streaming output
"""
import os
import sys
import time
import argparse
import torch
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tokenizer import BPETokenizer, BOS_ID, EOS_ID
from model import load_model


@torch.no_grad()
def generate(
    model,
    tokenizer: BPETokenizer,
    prompt: str,
    max_new_tokens: int = 200,
    temperature: float = 0.8,
    top_k: int = 40,
    top_p: float = 0.9,
    repetition_penalty: float = 1.2,
    device: torch.device = None,
    stop_token_ids: list = None,
) -> str:
    """生成 Logiko 文本（带重复惩罚）"""
    if device is None:
        device = next(model.parameters()).device
    model.eval()

    if stop_token_ids is None:
        stop_token_ids = [EOS_ID]

    # 编码 prompt
    ids = tokenizer.encode(prompt, add_bos=True, add_eos=False)
    if len(ids) == 0:
        ids = [BOS_ID]
    x = torch.tensor(ids, dtype=torch.long, device=device).unsqueeze(0)  # (1, T)

    generated = list(ids)
    seq_len = model.cfg.max_seq_len

    # 用于重复惩罚：记录最近出现的 token 频次
    recent_tokens = {}

    for step in range(max_new_tokens):
        x_in = x[:, -seq_len:]
        logits, _ = model(x_in, targets=None)
        logits = logits[:, -1, :]  # (1, V)

        # 重复惩罚：对最近出现的 token 降权
        if repetition_penalty != 1.0:
            for tok_id, count in recent_tokens.items():
                if count > 0:
                    if logits[0, tok_id] > 0:
                        logits[0, tok_id] /= repetition_penalty
                    else:
                        logits[0, tok_id] *= repetition_penalty

        if temperature <= 0:
            # greedy
            next_id = torch.argmax(logits, dim=-1, keepdim=True)
        else:
            logits = logits / temperature
            # top-k
            if top_k > 0:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits = logits.masked_fill(logits < v[:, [-1]], -float("inf"))
            # top-p
            if top_p < 1.0:
                sorted_logits, sorted_idx = torch.sort(logits, descending=True)
                cum_probs = F.softmax(sorted_logits, dim=-1).cumsum(dim=-1)
                mask = cum_probs > top_p
                mask[..., 1:] = mask[..., :-1].clone()
                mask[..., 0] = False
                sorted_logits = sorted_logits.masked_fill(mask, -float("inf"))
                # scatter back
                logits = torch.full_like(logits, -float("inf"))
                logits.scatter_(1, sorted_idx, sorted_logits)
            probs = F.softmax(logits, dim=-1)
            next_id = torch.multinomial(probs, num_samples=1)

        next_id_item = next_id.item()
        if next_id_item in stop_token_ids:
            break

        generated.append(next_id_item)
        x = torch.cat([x, next_id], dim=1)

        # 更新 recent_tokens（保留最近 64 个 token 的历史）
        recent_tokens[next_id_item] = recent_tokens.get(next_id_item, 0) + 1
        if len(generated) > 64:
            old_id = generated[-64]
            recent_tokens[old_id] = max(0, recent_tokens.get(old_id, 0) - 1)

    return tokenizer.decode(generated)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ckpt", default="/home/z/my-project/logiko/logiko_final.pt")
    p.add_argument("--prompt", default="### paragraph 9999")
    p.add_argument("--max_new_tokens", type=int, default=200)
    p.add_argument("--temperature", type=float, default=0.8)
    p.add_argument("--top_k", type=int, default=40)
    p.add_argument("--top_p", type=float, default=0.9)
    p.add_argument("--repetition_penalty", type=float, default=1.2)
    p.add_argument("--device", default="cpu")
    p.add_argument("--n_samples", type=int, default=3)
    p.add_argument("--no_repeat_ngram_size", type=int, default=0, help="0=disabled")
    args = p.parse_args()

    device = torch.device(args.device)
    print(f"Loading model from {args.ckpt}...")
    model, extra = load_model(args.ckpt, map_location=device)
    model.to(device)
    print(f"Model loaded. Step={extra.get('step', '?')}, loss={extra.get('loss', '?')}")
    print(f"Params: {model.num_parameters():,}")
    print(f"Decoding: T={args.temperature}, top_k={args.top_k}, top_p={args.top_p}, rep_penalty={args.repetition_penalty}")
    print()

    tokenizer = BPETokenizer.load("/home/z/my-project/logiko/tokenizer.json")

    for i in range(args.n_samples):
        print(f"=== Sample {i+1} ===")
        t0 = time.time()
        text = generate(
            model, tokenizer, args.prompt,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
            top_k=args.top_k,
            top_p=args.top_p,
            repetition_penalty=args.repetition_penalty,
            device=device,
        )
        dt = time.time() - t0
        print(text)
        print(f"--- {len(text)} chars in {dt:.2f}s ---\n")

    # 贪心解码对比
    print("=== Greedy (no rep penalty) ===")
    t0 = time.time()
    text = generate(
        model, tokenizer, args.prompt,
        max_new_tokens=args.max_new_tokens,
        temperature=0.0,
        repetition_penalty=1.0,  # disable
        device=device,
    )
    print(text)
    print(f"--- {len(text)} chars in {time.time()-t0:.2f}s ---")


if __name__ == "__main__":
    main()
