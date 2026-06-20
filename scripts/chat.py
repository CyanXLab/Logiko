#!/usr/bin/env python3
"""
Logiko Chat CLI
================
Interactive command-line Q&A loop with a trained Logiko model.

Usage:
    python3 chat.py
    python3 chat.py --ckpt logiko_sft_final.pt
    python3 chat.py --temperature 0.5 --top_k 30

Type 'exit', 'quit', or Ctrl+C to leave.
Type 'reset' to clear conversation history.
Type 'save <filename>' to save the conversation to a file.
"""
import os
import sys
import time
import argparse
import torch

# Make sibling modules importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tokenizer import BPETokenizer, BOS_ID, EOS_ID
from model import load_model
from generate import generate


# Default paths (relative to this file)
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CKPT = os.path.join(HERE, "..", "models", "logiko_sft_final.pt")
DEFAULT_TOK = os.path.join(HERE, "..", "models", "tokenizer.json")

# Fallback to logiko/ dir if not in models/
if not os.path.exists(DEFAULT_CKPT):
    DEFAULT_CKPT = os.path.join(HERE, "logiko_sft_final.pt")
if not os.path.exists(DEFAULT_TOK):
    DEFAULT_TOK = os.path.join(HERE, "tokenizer.json")


BANNER = r"""
 __                  ___  _
 / _\ ___ _ __ _   _ / _ \| |_
 \ \ / _ \ '__| | | | | | | __|
 _\ \  __/ |  | |_| | |_| | |_
 \__/\___|_|   \__, |\___/ \__|
               |___/

  Logiko interactive Q&A console.
  Type your question in Logiko and press Enter.
  Commands:  exit | quit | reset | save <file> | help
"""


def print_help():
    print("""
Commands:
  exit / quit     Leave the chat.
  reset           Clear conversation history.
  save <file>     Save conversation to file.
  help            Show this help.
  settings        Show current decoding settings.

Decoding parameters (can be set inline):
  :temp 0.5       Set temperature
  :topk 30        Set top-k
  :topp 0.9       Set top-p
  :rep 1.15       Set repetition penalty
  :max 80         Set max new tokens
""")


def parse_setting_cmd(line: str):
    """Parse ':temp 0.5' style commands. Returns (key, value) or None."""
    if not line.startswith(":"):
        return None
    parts = line[1:].split(None, 1)
    if len(parts) != 2:
        return None
    return parts[0].lower(), parts[1]


def main():
    p = argparse.ArgumentParser(description="Logiko interactive chat")
    p.add_argument("--ckpt", default=DEFAULT_CKPT, help="Path to model checkpoint")
    p.add_argument("--tokenizer", default=DEFAULT_TOK, help="Path to tokenizer.json")
    p.add_argument("--device", default="cpu")
    p.add_argument("--temperature", type=float, default=0.4)
    p.add_argument("--top_k", type=int, default=30)
    p.add_argument("--top_p", type=float, default=0.9)
    p.add_argument("--repetition_penalty", type=float, default=1.15)
    p.add_argument("--max_new_tokens", type=int, default=100)
    p.add_argument("--no_prompt_hint", action="store_true",
                   help="Don't auto-add answer hint (default: try to add a hint from the question)")
    args = p.parse_args()

    # Resolve paths
    ckpt_path = os.path.abspath(args.ckpt)
    tok_path = os.path.abspath(args.tokenizer)
    if not os.path.exists(ckpt_path):
        print(f"ERROR: checkpoint not found: {ckpt_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(tok_path):
        print(f"ERROR: tokenizer not found: {tok_path}", file=sys.stderr)
        sys.exit(1)

    device = torch.device(args.device)
    print(f"Loading tokenizer from {tok_path}...")
    tok = BPETokenizer.load(tok_path)
    print(f"Tokenizer vocab: {len(tok.vocab)}")

    print(f"Loading model from {ckpt_path}...")
    model, extra = load_model(ckpt_path, map_location=device)
    model.to(device)
    model.eval()
    print(f"Model loaded. step={extra.get('step')}, loss={extra.get('loss')}")
    print(f"Params: {model.num_parameters():,}")
    print(f"Device: {device}")
    print()

    # Decoding state
    state = {
        "temperature": args.temperature,
        "top_k": args.top_k,
        "top_p": args.top_p,
        "repetition_penalty": args.repetition_penalty,
        "max_new_tokens": args.max_new_tokens,
    }

    print(BANNER)
    print(f"Decoding: T={state['temperature']}, top_k={state['top_k']}, "
          f"top_p={state['top_p']}, rep_penalty={state['repetition_penalty']}, "
          f"max_new={state['max_new_tokens']}")
    print()

    conversation = []  # list of (role, text)

    # Some suggested opening questions
    suggestions = [
        "what be water?",
        "what be fire?",
        "what be sun?",
        "what be tree?",
        "what -a mean?",
        "what mal- mean?",
        "what ta mean?",
        "what be music?",
        "what be season?",
        "how say I love you in logiko?",
    ]

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye!")
            break

        if not user_input:
            continue

        # Commands
        if user_input in ("exit", "quit"):
            print("bye!")
            break
        if user_input == "help":
            print_help()
            continue
        if user_input == "settings":
            print(f"  temperature={state['temperature']}")
            print(f"  top_k={state['top_k']}")
            print(f"  top_p={state['top_p']}")
            print(f"  repetition_penalty={state['repetition_penalty']}")
            print(f"  max_new_tokens={state['max_new_tokens']}")
            continue
        if user_input == "reset":
            conversation.clear()
            print("(conversation history cleared)")
            continue
        if user_input.startswith("save "):
            fname = user_input[5:].strip()
            try:
                with open(fname, "w", encoding="utf-8") as f:
                    for role, text in conversation:
                        f.write(f"{role}: {text}\n")
                print(f"(saved to {fname})")
            except Exception as e:
                print(f"(save failed: {e})")
            continue
        if user_input == "suggest":
            print("Try asking:")
            for s in suggestions:
                print(f"  - {s}")
            continue

        # Settings commands
        setting = parse_setting_cmd(user_input)
        if setting is not None:
            key, val = setting
            try:
                if key in ("temp", "temperature"):
                    state["temperature"] = float(val)
                    print(f"  temperature = {state['temperature']}")
                elif key in ("topk", "top_k"):
                    state["top_k"] = int(val)
                    print(f"  top_k = {state['top_k']}")
                elif key in ("topp", "top_p"):
                    state["top_p"] = float(val)
                    print(f"  top_p = {state['top_p']}")
                elif key in ("rep", "repetition_penalty"):
                    state["repetition_penalty"] = float(val)
                    print(f"  repetition_penalty = {state['repetition_penalty']}")
                elif key in ("max", "max_new_tokens"):
                    state["max_new_tokens"] = int(val)
                    print(f"  max_new_tokens = {state['max_new_tokens']}")
                else:
                    print(f"  unknown setting: {key}")
            except ValueError:
                print(f"  invalid value: {val}")
            continue

        # Build prompt. Use Q:/A: format with a hint.
        # Heuristic: try to extract the topic word to use as answer hint.
        # For "what be X?" we add "X" as the start of the answer.
        hint = ""
        if not args.no_prompt_hint:
            lower = user_input.lower()
            if lower.startswith("what be ") and lower.endswith("?"):
                topic = lower[len("what be "):-1].strip()
                # remove leading "one " etc
                if topic.startswith("one "):
                    topic = topic[4:]
                hint = " " + topic
            elif lower.startswith("what ") and " mean?" in lower:
                # "what -a mean?" -> hint "suffix"
                # extract the morpheme
                morpheme = lower[len("what "):].split(" mean?")[0].strip()
                # suffixes
                if morpheme in ("-a", "-e", "-ist", "-ej", "-il", "-ec", "-in", "-id"):
                    hint = " suffix" if morpheme in ("-a", "-e") else " " + morpheme.lstrip("-")
                else:
                    hint = " " + morpheme
            elif lower.startswith("what ta mean?"):
                hint = " ta"
            elif lower.startswith("how say "):
                # "how say I love you in logiko?" -> hint nothing
                hint = ""

        prompt = f"Q: {user_input}\nA:{hint}"

        t0 = time.time()
        try:
            output = generate(
                model, tok, prompt,
                max_new_tokens=state["max_new_tokens"],
                temperature=state["temperature"],
                top_k=state["top_k"],
                top_p=state["top_p"],
                repetition_penalty=state["repetition_penalty"],
                device=device,
            )
        except KeyboardInterrupt:
            print("(interrupted)")
            continue

        dt = time.time() - t0

        # Extract just the answer part (after "A:")
        if "A:" in output:
            answer = output.split("A:", 1)[1].strip()
        else:
            answer = output

        # Remove leading hint from answer if it's there
        if hint and answer.startswith(hint.strip()):
            answer = answer[len(hint.strip()):].strip()

        print(f"ai> {answer}")
        print(f"   [{len(answer)} chars, {dt:.2f}s]")

        conversation.append(("you", user_input))
        conversation.append(("ai", answer))


if __name__ == "__main__":
    main()
