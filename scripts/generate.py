#!/usr/bin/env python3
"""
Logiko Text Generation v3
==========================
Improvements:
  - Repetition penalty
  - Frequency penalty (penalize tokens already used many times)
  - Presence penalty (penalize tokens already used at all)
  - Top-k / top-p / temperature sampling
  - No-repeat n-gram (optional)
  - Better EOS handling
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
    frequency_penalty: float = 0.3,
    presence_penalty: float = 0.2,
    no_repeat_ngram_size: int = 0,
    device: torch.device = None,
    stop_token_ids: list = None,
) -> str:
    """Generate Logiko text with multiple anti-repetition strategies.

    Penalties (OpenAI-style):
      - repetition_penalty: multiplicative penalty on recently appeared tokens
      - frequency_penalty:  additive penalty proportional to token count
      - presence_penalty:   additive penalty if token has appeared at all
      - no_repeat_ngram_size: forbid any n-gram of this size from repeating
    """
    if device is None:
        device = next(model.parameters()).device
    model.eval()

    if stop_token_ids is None:
        stop_token_ids = [EOS_ID]

    ids = tokenizer.encode(prompt, add_bos=True, add_eos=False)
    if len(ids) == 0:
        ids = [BOS_ID]
    x = torch.tensor(ids, dtype=torch.long, device=device).unsqueeze(0)

    generated = list(ids)
    seq_len = model.cfg.max_seq_len

    # Track all generated tokens for frequency/presence
    token_counts = {}
    for t in generated:
        token_counts[t] = token_counts.get(t, 0) + 1

    for step in range(max_new_tokens):
        x_in = x[:, -seq_len:]
        logits, _ = model(x_in, targets=None)
        logits = logits[:, -1, :].clone()  # (1, V) — clone so we can modify

        # === Penalties ===
        # 1. Repetition penalty (multiplicative, on recent context only)
        if repetition_penalty != 1.0:
            recent = set(generated[-64:])  # look at last 64 tokens
            for tok_id in recent:
                if logits[0, tok_id] > 0:
                    logits[0, tok_id] /= repetition_penalty
                else:
                    logits[0, tok_id] *= repetition_penalty

        # 2. Frequency penalty (additive, proportional to count)
        if frequency_penalty > 0:
            for tok_id, count in token_counts.items():
                logits[0, tok_id] -= frequency_penalty * count

        # 3. Presence penalty (additive, flat if token has appeared)
        if presence_penalty > 0:
            for tok_id in token_counts:
                logits[0, tok_id] -= presence_penalty

        # 4. No-repeat n-gram
        if no_repeat_ngram_size > 0 and len(generated) >= no_repeat_ngram_size:
            ngram = tuple(generated[-no_repeat_ngram_size + 1:])
            banned = set()
            # find all positions where this (n-1)-gram appears, then ban the next token
            for i in range(len(generated) - no_repeat_ngram_size + 1):
                if tuple(generated[i:i + no_repeat_ngram_size - 1]) == ngram:
                    banned.add(generated[i + no_repeat_ngram_size - 1])
            for tok_id in banned:
                logits[0, tok_id] = -float("inf")

        # === Sampling ===
        if temperature <= 0:
            next_id = torch.argmax(logits, dim=-1, keepdim=True)
        else:
            logits = logits / max(temperature, 1e-5)
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
                logits = torch.full_like(logits, -float("inf"))
                logits.scatter_(1, sorted_idx, sorted_logits)
            probs = F.softmax(logits, dim=-1)
            next_id = torch.multinomial(probs, num_samples=1)

        next_id_item = next_id.item()
        if next_id_item in stop_token_ids:
            break

        generated.append(next_id_item)
        token_counts[next_id_item] = token_counts.get(next_id_item, 0) + 1
        x = torch.cat([x, next_id], dim=1)

    return tokenizer.decode(generated)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ckpt", default="/home/z/my-project/logiko/logiko_sft_final.pt")
    p.add_argument("--prompt", default="### paragraph 9999")
    p.add_argument("--max_new_tokens", type=int, default=200)
    p.add_argument("--temperature", type=float, default=0.8)
    p.add_argument("--top_k", type=int, default=40)
    p.add_argument("--top_p", type=float, default=0.9)
    p.add_argument("--repetition_penalty", type=float, default=1.15)
    p.add_argument("--frequency_penalty", type=float, default=0.3)
    p.add_argument("--presence_penalty", type=float, default=0.2)
    p.add_argument("--no_repeat_ngram_size", type=int, default=3)
    p.add_argument("--device", default="cpu")
    p.add_argument("--n_samples", type=int, default=3)
    p.add_argument("--seed", type=int, default=-1, help="-1 for random seed")
    args = p.parse_args()

    if args.seed >= 0:
        torch.manual_seed(args.seed)

    device = torch.device(args.device)
    print(f"Loading model from {args.ckpt}...")
    model, extra = load_model(args.ckpt, map_location=device)
    model.to(device)
    print(f"Model loaded. Step={extra.get('step', '?')}, loss={extra.get('loss', '?')}")
    print(f"Params: {model.num_parameters():,}")
    print(f"Decoding: T={args.temperature}, top_k={args.top_k}, top_p={args.top_p}, "
          f"rep={args.repetition_penalty}, freq={args.frequency_penalty}, "
          f"pres={args.presence_penalty}, no_repeat_ngram={args.no_repeat_ngram_size}")
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
            frequency_penalty=args.frequency_penalty,
            presence_penalty=args.presence_penalty,
            no_repeat_ngram_size=args.no_repeat_ngram_size,
            device=device,
        )
        dt = time.time() - t0
        print(text)
        print(f"--- {len(text)} chars in {dt:.2f}s ---\n")


if __name__ == "__main__":
    main()
