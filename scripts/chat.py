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
  single               Single-turn mode (default, each Q answered independently).
  multi                Multi-turn context mode (may degrade on long sessions).
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


def is_followup_question(new_question, history):
    """Detect if new question is a follow-up to recent conversation.
    
    Returns True if the question references prior context (pronouns, 
    topic continuity, short questions like "how about X?", "cu ta...?").
    """
    if not history:
        return False
    q_lower = new_question.lower().strip().rstrip("?!.")
    
    # Pronoun references (ta = it/he/she, this, that)
    pronoun_indicators = ["ta ", "ta?", "this", "that", "ta-many"]
    for p in pronoun_indicators:
        if p in q_lower:
            return True
    
    # Short follow-up patterns
    short_patterns = ["how about", "what about", "cu ta", "why ta", "how ta",
                      "and ta", "but ta", "so ta", "then ta"]
    for p in short_patterns:
        if q_lower.startswith(p):
            return True
    
    # Very short questions (< 25 chars) likely follow-ups
    if len(q_lower) < 25:
        return True
    
    # Check topic continuity: if new question contains a noun from recent AI answer
    recent_ai_answers = [text for role, text in history[-4:] if role == "ai"]
    if recent_ai_answers:
        # Get last AI answer's key words
        last_answer = recent_ai_answers[-1].lower()
        # Simple: check if any word > 3 chars from question appears in answer
        q_words = [w for w in q_lower.split() if len(w) > 3]
        for w in q_words:
            if w in last_answer:
                return True
    
    return False


def build_prompt(history, new_question, max_chars=800, hint="", max_turns=4):
    """Build a multi-turn prompt from conversation history (v2: limited turns).
    
    v2 improvements:
    - Default max_chars=800 (was 1500) to avoid long context degradation
    - max_turns=4: only keep last 2 Q-A pairs (4 turns) max
    - This prevents small model from being overwhelmed by long history
    
    history: list of (role, text) tuples (role in {"user", "ai"})
    new_question: the new user question
    max_chars: soft limit on total length
    hint: hint to prepend to answer
    
    Returns: prompt string, n_turns_included
    """
    # Only keep last few turns (max_turns = 4 means 2 Q-A pairs)
    recent_history = history[-max_turns:] if len(history) > max_turns else history
    
    # Build turns from recent history
    turns = []
    for role, text in recent_history:
        if role == "user":
            turns.append(f"Q: {text}")
        else:
            turns.append(f"A: {text}")
    turns.append(f"Q: {new_question}")
    turns.append(f"A:{hint}")
    
    # If still too long, drop oldest turns
    while sum(len(t) for t in turns) > max_chars and len(turns) > 3:
        turns.pop(0)
        turns.pop(0)
    
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


def normalize_question(question):
    """Normalize user input: add '?' if missing for question patterns.
    
    This handles cases where user types 'what be fire' instead of 'what be fire?'
    """
    q = question.strip()
    # If already ends with ?, return as-is
    if q.endswith("?") or q.endswith("!") or q.endswith("."):
        return q
    # Question patterns that should end with ?
    lower = q.lower()
    question_patterns = [
        "what ", "who ", "where ", "when ", "why ", "how ", "cu ",
        "is ", "are ", "do ", "did ", "does ", "can ", "could ",
        "will ", "would ", "should ", "may ", "might ",
    ]
    for pat in question_patterns:
        if lower.startswith(pat):
            return q + "?"
    # Default: return as-is
    return q


def compute_hint(question):
    """Generate a hint to prepend to "A:" for better grounding.
    
    For "what be X?" questions, prepend " X" so the model continues from X.
    For other questions, return "".
    
    Works with or without trailing '?'.
    """
    # Normalize: strip trailing punctuation for matching
    lower = question.lower().strip().rstrip("?!.") 
    # what be X?
    if lower.startswith("what be "):
        topic = lower[len("what be "):].strip()
        if topic.startswith("one "):
            topic = topic[4:]
        if topic and len(topic) < 30 and " " not in topic:
            # Single-word topic — strong hint
            return " " + topic
        elif topic and len(topic) < 30:
            # Multi-word topic — still useful
            return " " + topic
    # what X mean?
    if lower.startswith("what ") and " mean" in lower:
        morpheme = lower[len("what "):].split(" mean")[0].strip()
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
    # how about X?
    if lower.startswith("how about "):
        topic = lower[len("how about "):].strip()
        if topic:
            return " " + topic
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
    p.add_argument("--single_turn", action="store_true",
                   help="Force single-turn mode (no context, each Q independent)")
    p.add_argument("--multi_turn", action="store_true", default=True,
                   help="Use multi-turn context mode (default, with smart follow-up detection)")
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
        "max_context_chars": 800,  # v2: reduced from 1200 for small model
        "multi_turn": not args.single_turn,  # v2: default True (multi with smart detection)
    }

    print(BANNER)
    mode_str = "multi-turn (smart follow-up detection)" if state["multi_turn"] else "single-turn (no context)"
    print(f"Mode: {mode_str}")
    print(f"  (type 'multi' or 'single' to switch; multi mode auto-detects follow-up questions)")
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
        if user_input in ("multi", "/multi"):
            state["multi_turn"] = True
            print("(multi-turn context mode: ON)")
            continue
        if user_input in ("single", "/single"):
            state["multi_turn"] = False
            print("(single-turn mode: ON — each question answered independently)")
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

        # Normalize: add '?' if missing for question patterns
        normalized_input = normalize_question(user_input)
        
        # Compute hint based on normalized input
        hint = "" if args.no_hint else compute_hint(normalized_input)

        # Decide whether to use multi-turn context
        # v2: smart context usage
        # - If multi_turn mode is ON and question is a follow-up, use context
        # - If question is NOT a follow-up (new topic), use single-turn even in multi mode
        # - If multi_turn mode is OFF, always single-turn
        use_context = False
        if state.get("multi_turn", True) and conversation:
            if is_followup_question(normalized_input, conversation):
                use_context = True
            # else: new topic, single-turn is better
        
        if use_context:
            prompt, n_turns = build_prompt(
                conversation, normalized_input,
                max_chars=state["max_context_chars"],
                hint=hint,
            )
        else:
            prompt = f"Q: {normalized_input}\nA:{hint}"
            n_turns = 0

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
        
        # Sanity check: if answer is too short (< 20 chars) or looks like a question,
        # retry without context (single-turn fallback)
        if len(answer) < 20 or answer.endswith("?") or answer.endswith(":"):
            single_prompt = f"Q: {normalized_input}\nA:{hint}"
            retry_output = generate_with_penalties(
                model, tok, single_prompt,
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
            retry_answer = extract_answer(retry_output, hint=hint)
            if len(retry_answer) > len(answer) + 10:
                answer = retry_answer
                n_turns = 0

        # Show context indicator
        ctx_indicator = f"ctx={n_turns} turns" if use_context else "no context"
        print(f"ai> {answer}")
        print(f"   [{len(answer)} chars, {dt:.2f}s, {ctx_indicator}]")

        # Add to conversation history (use normalized input)
        conversation.append(("user", normalized_input))
        conversation.append(("ai", answer))


if __name__ == "__main__":
    main()
