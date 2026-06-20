#!/usr/bin/env python3
"""
Logiko Chat CLI v2 — Multi-turn Context
=========================================
Improvements over v1:
  - Multi-turn context: full conversation history is fed to the model
  - Sliding window: when history exceeds max_seq_len, oldest turns are dropped
  - Better diversity: default temperature=0.85, with frequency/presence penalty
  - Live decoding settings (:temp, :topk, :topp, :rep, :freq, :pres, :max)
  - Save/load conversation
  - Topic-aware answer hint (auto-detect "what be X?" and prepend "X" as start)

Usage:
    python3 chat.py
    python3 chat.py --ckpt logiko_sft_final.pt
    python3 chat.py --temperature 0.9 --no_hint

Type 'exit', 'quit', or Ctrl+C to leave.
Type 'help' for command list.
"""
import os
import sys
import time
import argparse
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tokenizer import BPETokenizer, BOS_ID, EOS_ID
from model import load_model
from generate import generate as generate_with_penalties


HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CKPT = os.path.join(HERE, "..", "models", "logiko_sft_final.pt")
DEFAULT_TOK = os.path.join(HERE, "..", "models", "tokenizer.json")

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

  Logiko v2 — Multi-turn Q&A console.
  Conversation history is preserved within session.
  Commands:  exit | quit | reset | save <file> | load <file> | help | settings | suggest
"""


def print_help():
    print("""
Commands:
  exit / quit          Leave the chat.
  reset                Clear conversation history.
  save <file>          Save conversation to file.
  load <file>          Load conversation from file.
  help                 Show this help.
  settings             Show current decoding settings.
  suggest              Show suggested opening questions.
  tokens               Show current token count of context.

Decoding parameters (set inline with ':'):
  :temp 0.85           Set temperature (higher = more random)
  :topk 40             Set top-k
  :topp 0.9            Set top-p
  :rep 1.15            Set repetition penalty
  :freq 0.3            Set frequency penalty
  :pres 0.2            Set presence penalty
  :max 100             Set max new tokens
  :ngram 3             Set no_repeat_ngram_size (0 to disable)
""")


def parse_setting_cmd(line: str):
    if not line.startswith(":"):
        return None
    parts = line[1:].split(None, 1)
    if len(parts) != 2:
        return None
    return parts[0].lower(), parts[1]


def build_prompt(history, new_question, max_chars=1500, hint=""):
    """Build a multi-turn prompt from conversation history.
    
    history: list of (role, text) tuples (role in {"user", "ai"})
    new_question: the new user question
    max_chars: soft limit; older turns are dropped if exceeded
    
    Returns: prompt string, n_turns_included
    """
    # Build turns from history
    turns = []
    for role, text in history:
        if role == "user":
            turns.append(f"Q: {text}")
        else:
            turns.append(f"A: {text}")
    turns.append(f"Q: {new_question}")
    turns.append(f"A:{hint}")
    
    # If too long, drop oldest turns (keep first Q and most recent)
    while sum(len(t) for t in turns) > max_chars and len(turns) > 3:
        # Drop oldest complete Q-A pair (first 2 elements, but keep first Q if it's the opening)
        if len(turns) > 3:
            turns.pop(0)
            turns.pop(0)
        else:
            break
    
    return "\n".join(turns), len(turns)


def extract_answer(generated_text, hint=""):
    """Extract just the answer part from generated text.
    
    generated_text: full model output
    hint: the hint we prepended (e.g., " water")
    
    Returns: just the answer portion (after last "A:")
    """
    # Find last "A:"
    if "A:" in generated_text:
        answer = generated_text.rsplit("A:", 1)[1].strip()
    else:
        answer = generated_text
    
    # Remove the hint if it's at the start
    if hint:
        hint_stripped = hint.strip()
        if hint_stripped and answer.startswith(hint_stripped):
            answer = answer[len(hint_stripped):].strip()
    
    # Cut off at EOS or any new "Q:" that might appear (hallucinated next turn)
    if "\nQ:" in answer:
        answer = answer.split("\nQ:")[0].strip()
    if "<eos>" in answer:
        answer = answer.split("<eos>")[0].strip()
    
    return answer


def compute_hint(question):
    """Generate a hint to prepend to "A:" for better grounding.
    
    For "what be X?" questions, prepend " X" so the model continues from X.
    For other questions, return "".
    """
    lower = question.lower().strip()
    # what be X?
    if lower.startswith("what be ") and lower.endswith("?"):
        topic = lower[len("what be "):-1].strip()
        if topic.startswith("one "):
            topic = topic[4:]
        if topic and len(topic) < 30:
            return " " + topic
    # what X mean?
    if lower.startswith("what ") and " mean?" in lower:
        morpheme = lower[len("what "):].split(" mean?")[0].strip()
        if morpheme in ("-a", "-e"):
            return " suffix"
        if morpheme in ("-ist", "-ej", "-il", "-ec", "-uc", "-in", "-id", "-em", "-abl"):
            return " " + morpheme.lstrip("-")
        if morpheme == "mal-":
            return " prefix"
        if morpheme == "cu":
            return " cu"
        if morpheme == "ta":
            return " ta"
        return ""
    # how say X in logiko?
    if lower.startswith("how say ") and "in logiko" in lower:
        return ""
    # how form X?
    if lower.startswith("how form "):
        return ""
    # how about X?
    if lower.startswith("how about "):
        topic = lower[len("how about "):].rstrip("?").strip()
        if topic:
            return " " + topic
    # which be more X: A or B?
    if lower.startswith("which be more ") and "?" in lower:
        return ""
    return ""


def main():
    p = argparse.ArgumentParser(description="Logiko v2 interactive chat with multi-turn context")
    p.add_argument("--ckpt", default=DEFAULT_CKPT, help="Path to model checkpoint")
    p.add_argument("--tokenizer", default=DEFAULT_TOK, help="Path to tokenizer.json")
    p.add_argument("--device", default="cpu")
    # Decoding defaults — more diverse than v1
    p.add_argument("--temperature", type=float, default=0.85, help="Higher = more random")
    p.add_argument("--top_k", type=int, default=40)
    p.add_argument("--top_p", type=float, default=0.9)
    p.add_argument("--repetition_penalty", type=float, default=1.15)
    p.add_argument("--frequency_penalty", type=float, default=0.3)
    p.add_argument("--presence_penalty", type=float, default=0.2)
    p.add_argument("--no_repeat_ngram_size", type=int, default=3)
    p.add_argument("--max_new_tokens", type=int, default=120)
    p.add_argument("--max_context_chars", type=int, default=1200,
                   help="Soft limit on context length (chars); older turns dropped beyond this")
    p.add_argument("--no_hint", action="store_true",
                   help="Don't auto-add answer hint")
    p.add_argument("--seed", type=int, default=-1, help="-1 for random seed")
    args = p.parse_args()

    if args.seed >= 0:
        torch.manual_seed(args.seed)
        random_seed = args.seed
    else:
        random_seed = None

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
    print(f"Params: {model.num_parameters():,}, max_seq_len: {model.cfg.max_seq_len}")
    print(f"Device: {device}")
    print()

    state = {
        "temperature": args.temperature,
        "top_k": args.top_k,
        "top_p": args.top_p,
        "repetition_penalty": args.repetition_penalty,
        "frequency_penalty": args.frequency_penalty,
        "presence_penalty": args.presence_penalty,
        "no_repeat_ngram_size": args.no_repeat_ngram_size,
        "max_new_tokens": args.max_new_tokens,
        "max_context_chars": args.max_context_chars,
    }

    print(BANNER)
    print(f"Decoding: T={state['temperature']}, top_k={state['top_k']}, "
          f"top_p={state['top_p']}, rep={state['repetition_penalty']}, "
          f"freq={state['frequency_penalty']}, pres={state['presence_penalty']}, "
          f"ngram={state['no_repeat_ngram_size']}, max_new={state['max_new_tokens']}")
    print(f"Context: max {state['max_context_chars']} chars (~{state['max_context_chars']//4} tokens)")
    print()

    conversation = []  # list of (role, text)

    suggestions = [
        "what be water?",
        "what be fire?",
        "what be sun?",
        "what be tree?",
        "what -a mean?",
        "what mal- mean?",
        "what cu mean?",
        "what ta mean?",
        "how say I love you in logiko?",
        "what be music?",
        "what be season?",
        "how form past tense?",
        "how say my in logiko?",
        "what be computer?",
        "what be time?",
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
            for k, v in state.items():
                print(f"  {k} = {v}")
            continue
        if user_input == "reset":
            conversation.clear()
            print("(conversation history cleared)")
            continue
        if user_input == "tokens":
            # Estimate token count of current context
            prompt, n = build_prompt(conversation, "test", state["max_context_chars"])
            ids = tok.encode(prompt, add_bos=True, add_eos=False)
            print(f"  Current context (with 'test' as new Q): {len(ids)} tokens, {n} turns")
            continue
        if user_input == "suggest":
            print("Try asking:")
            for s in suggestions:
                print(f"  - {s}")
            continue
        if user_input.startswith("save "):
            fname = user_input[5:].strip()
            try:
                with open(fname, "w", encoding="utf-8") as f:
                    for role, text in conversation:
                        prefix = "you" if role == "user" else "ai"
                        f.write(f"{prefix}> {text}\n")
                print(f"(saved to {fname})")
            except Exception as e:
                print(f"(save failed: {e})")
            continue
        if user_input.startswith("load "):
            fname = user_input[5:].strip()
            try:
                with open(fname, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                conversation.clear()
                for line in lines:
                    line = line.rstrip("\n")
                    if line.startswith("you> "):
                        conversation.append(("user", line[5:]))
                    elif line.startswith("ai> "):
                        conversation.append(("ai", line[4:]))
                print(f"(loaded {len(conversation)} turns from {fname})")
            except Exception as e:
                print(f"(load failed: {e})")
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
                elif key in ("freq", "frequency_penalty"):
                    state["frequency_penalty"] = float(val)
                    print(f"  frequency_penalty = {state['frequency_penalty']}")
                elif key in ("pres", "presence_penalty"):
                    state["presence_penalty"] = float(val)
                    print(f"  presence_penalty = {state['presence_penalty']}")
                elif key in ("ngram", "no_repeat_ngram_size"):
                    state["no_repeat_ngram_size"] = int(val)
                    print(f"  no_repeat_ngram_size = {state['no_repeat_ngram_size']}")
                elif key in ("max", "max_new_tokens"):
                    state["max_new_tokens"] = int(val)
                    print(f"  max_new_tokens = {state['max_new_tokens']}")
                elif key in ("ctx", "max_context_chars"):
                    state["max_context_chars"] = int(val)
                    print(f"  max_context_chars = {state['max_context_chars']}")
                else:
                    print(f"  unknown setting: {key}")
            except ValueError:
                print(f"  invalid value: {val}")
            continue

        # Compute hint
        hint = "" if args.no_hint else compute_hint(user_input)

        # Build multi-turn prompt
        prompt, n_turns = build_prompt(
            conversation, user_input,
            max_chars=state["max_context_chars"],
            hint=hint,
        )

        # Generate
        t0 = time.time()
        try:
            output = generate_with_penalties(
                model, tok, prompt,
                max_new_tokens=state["max_new_tokens"],
                temperature=state["temperature"],
                top_k=state["top_k"],
                top_p=state["top_p"],
                repetition_penalty=state["repetition_penalty"],
                frequency_penalty=state["frequency_penalty"],
                presence_penalty=state["presence_penalty"],
                no_repeat_ngram_size=state["no_repeat_ngram_size"],
                device=device,
            )
        except KeyboardInterrupt:
            print("(interrupted)")
            continue
        dt = time.time() - t0

        # Extract just the answer
        answer = extract_answer(output, hint=hint)

        print(f"ai> {answer}")
        print(f"   [{len(answer)} chars, {dt:.2f}s, ctx={n_turns} turns]")

        # Add to conversation history
        conversation.append(("user", user_input))
        conversation.append(("ai", answer))


if __name__ == "__main__":
    main()
