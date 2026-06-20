#!/usr/bin/env python3
"""
Logiko Tokenizer v6 (SentencePiece-style)
=========================================
Design:
  - Use ▁ (U+2581) as the space marker, like SentencePiece.
  - Encode: split text on whitespace; prepend ▁ to each piece; BPE-merge.
  - Each piece is its own "word": "▁hello", "▁,", "▁3", "▁###", etc.
  - Decode: replace ▁ with space; strip leading space.
  - This naturally handles all spacing: "result be -1." becomes
    ["▁result", "▁be", "▁-1", "▁."] wait — actually we split on whitespace,
    so "-1." is one piece → "▁-1." → BPE to ["▁-", "1", "."] or similar.
    No — we DON'T split pieces inside a whitespace token. The whole token
    is one BPE word.

Actually let's use the simpler rule:
  - Split on whitespace. Each whitespace-separated token is one piece.
  - Prepend ▁.
  - BPE on the whole piece (including punctuation).
  - Decode: replace ▁ with space, strip leading.

This makes round-trip EXACT.
"""
import os
import json
from collections import Counter
from typing import List, Dict, Tuple

SPECIAL_TOKENS = ["<pad>", "<bos>", "<eos>", "<unk>"]
PAD_ID, BOS_ID, EOS_ID, UNK_ID = 0, 1, 2, 3
SPACE = "▁"  # U+2581


class BPETokenizer:
    def __init__(self, vocab_size: int = 1500):
        self.target_vocab_size = vocab_size
        self.merges: List[Tuple[str, str]] = []
        self.vocab: List[str] = []
        self.token_to_id: Dict[str, int] = {}
        self.id_to_token: Dict[int, str] = {}
        self.merge_ranks: Dict[Tuple[str, str], int] = {}
        self._cache: Dict[str, List[str]] = {}

    def _get_word_freqs(self, text: str) -> Counter:
        """每个 whitespace-separated word -> '▁h e l l o' -> freq"""
        freqs = Counter()
        for line in text.split("\n"):
            for word in line.split():
                if not word:
                    continue
                # 第一个字符加 ▁ 前缀
                chars = " ".join([SPACE + word[0]] + list(word[1:]))
                freqs[chars] += 1
            # 行尾：用一个特殊 token 表示换行
        return freqs

    def _get_pair_stats(self, word_freqs: Counter) -> Counter:
        pairs = Counter()
        for word, freq in word_freqs.items():
            symbols = word.split()
            for i in range(len(symbols) - 1):
                pairs[(symbols[i], symbols[i + 1])] += freq
        return pairs

    def _merge_pair(self, pair: Tuple[str, str], word_freqs: Counter) -> Counter:
        new_freqs = Counter()
        bigram = " ".join(pair)
        replacement = pair[0] + pair[1]
        for word, freq in word_freqs.items():
            new_word = word.replace(bigram, replacement)
            new_freqs[new_word] += freq
        return new_freqs

    def train(self, text: str, verbose: bool = False):
        # 初始词表：
        #   - 特殊 token
        #   - 所有字符（包括 ▁）
        #   - ▁ + 每个字符（让单字符词也能被表示，如 ▁5, ▁I, ▁A）
        #   - 换行
        chars = sorted(set(text))
        chars = [c for c in chars if c not in (" ", "\n", "\t")]
        if SPACE not in chars:
            chars.append(SPACE)
        # 强制加入 Logiko 规范要求的标点（即使语料中没出现）
        REQUIRED_PUNCT = list(".,!?;:#-()/+=*")
        for p in REQUIRED_PUNCT:
            if p not in chars:
                chars.append(p)
        # 强制加入大写字母（虽然 Logiko 默认小写，但专有名词可能用到）
        for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if c not in chars:
                chars.append(c)
        chars = sorted(set(chars))
        special = list(SPECIAL_TOKENS)

        # ▁ + 字符 的组合
        space_chars = [SPACE + c for c in chars if c != SPACE]

        self.vocab = special + chars + space_chars + ["\n"]
        self.token_to_id = {t: i for i, t in enumerate(self.vocab)}
        self.id_to_token = {i: t for t, i in self.token_to_id.items()}

        word_freqs = self._get_word_freqs(text)
        n_merges = max(0, self.target_vocab_size - len(self.vocab))
        for i in range(n_merges):
            pair_stats = self._get_pair_stats(word_freqs)
            if not pair_stats:
                break
            best_pair = pair_stats.most_common(1)[0][0]
            word_freqs = self._merge_pair(best_pair, word_freqs)
            self.merges.append(best_pair)
            merged = best_pair[0] + best_pair[1]
            if merged not in self.token_to_id:
                self.token_to_id[merged] = len(self.vocab)
                self.id_to_token[len(self.vocab)] = merged
                self.vocab.append(merged)
            if verbose and (i + 1) % 100 == 0:
                print(f"  BPE merge {i+1}/{n_merges}: vocab_size={len(self.vocab)}, pair={best_pair}")

        self._build_merge_ranks()
        print(f"Tokenizer trained. Final vocab size: {len(self.vocab)} (merges: {len(self.merges)})")

    def _build_merge_ranks(self):
        self.merge_ranks = {pair: i for i, pair in enumerate(self.merges)}

    def _bpe_word(self, word: str) -> List[str]:
        """BPE-tokenize one whitespace-separated word. Returns list of subtokens.
        The first subtoken starts with ▁."""
        if word in self._cache:
            return self._cache[word]
        symbols = [SPACE + word[0]] + list(word[1:])
        while len(symbols) > 1:
            best_rank = float("inf")
            best_idx = -1
            for i in range(len(symbols) - 1):
                pair = (symbols[i], symbols[i + 1])
                rank = self.merge_ranks.get(pair)
                if rank is not None and rank < best_rank:
                    best_rank = rank
                    best_idx = i
            if best_idx < 0:
                break
            merged = symbols[best_idx] + symbols[best_idx + 1]
            symbols = symbols[:best_idx] + [merged] + symbols[best_idx + 2:]
        self._cache[word] = symbols
        return symbols

    def encode(self, text: str, add_bos: bool = True, add_eos: bool = False) -> List[int]:
        ids = []
        if add_bos:
            ids.append(BOS_ID)
        for line_idx, line in enumerate(text.split("\n")):
            if line_idx > 0:
                ids.append(self.token_to_id["\n"])
            for word in line.split():
                if not word:
                    continue
                for t in self._bpe_word(word):
                    ids.append(self.token_to_id.get(t, UNK_ID))
        if add_eos:
            ids.append(EOS_ID)
        return ids

    def decode(self, ids: List[int]) -> str:
        """Reconstruct text. ▁ means space; \n means newline."""
        out_lines = []
        cur_line = ""
        for i in ids:
            if i in (PAD_ID, BOS_ID, EOS_ID):
                continue
            t = self.id_to_token.get(i, "<unk>")
            if t == "<unk>":
                continue
            if t == "\n":
                out_lines.append(cur_line)
                cur_line = ""
                continue
            # 把 ▁ 替换成空格
            t = t.replace(SPACE, " ")
            cur_line += t
        if cur_line:
            out_lines.append(cur_line)
        # 每行 strip 头部空格（因为 ▁ 产生的空格在词首）
        out_lines = [line.lstrip() if i == 0 else line.lstrip() for i, line in enumerate(out_lines)]
        return "\n".join(out_lines).rstrip()

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            "vocab": self.vocab,
            "merges": self.merges,
            "target_vocab_size": self.target_vocab_size,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Tokenizer saved to {path}")

    @classmethod
    def load(cls, path: str) -> "BPETokenizer":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tok = cls(vocab_size=data["target_vocab_size"])
        tok.vocab = data["vocab"]
        tok.merges = [tuple(p) for p in data["merges"]]
        tok.token_to_id = {t: i for i, t in enumerate(tok.vocab)}
        tok.id_to_token = {i: t for t, i in tok.token_to_id.items()}
        tok._build_merge_ranks()
        return tok


def main():
    corpus_path = "/home/z/my-project/download/logiko_corpus.txt"
    print(f"Loading corpus from {corpus_path}...")
    with open(corpus_path, "r", encoding="utf-8") as f:
        text = f.read()
    print(f"Corpus: {len(text)} chars")

    tok = BPETokenizer(vocab_size=1500)
    print("Training BPE tokenizer (target vocab=1500)...")
    tok.train(text, verbose=True)

    save_path = "/home/z/my-project/logiko/tokenizer.json"
    tok.save(save_path)

    test_cases = [
        "I tomorrow will fast-e go to learn-ej.",
        "### paragraph 1234",
        "if we add 17 and 14, result be 31.",
        "if we subtract 7 from 6, result be -1.",
        "A: hello! B: hi, how are you?",
        "that 5 mal-rare-a clean-a star did be hear by I.",
        "news from city: mountain will warn mal-more-a particle.",
        "Yesterday, that mal-good-a teach-ist did fast-e eat one big-a apple in learn-ej, because ta mal-have hungry, so ta mal-do work.",
        "B: oil sense that nine result.",
        "if we multiply 5 by 8, result be 40.",
        "12 + 14 = 26",
        "Hello, world!",
        "### paragraph 5\nThis is a test.",
    ]
    print("\n=== Round-trip verification ===")
    all_pass = True
    for test in test_cases:
        ids = tok.encode(test, add_bos=False, add_eos=False)
        decoded = tok.decode(ids)
        n_unk = ids.count(UNK_ID)
        match = (test == decoded)
        if not match or n_unk > 0:
            all_pass = False
        status = "OK" if (match and n_unk == 0) else "FAIL"
        print(f"\n  [{status}] Input:   {repr(test)}")
        print(f"         Tokens:  {len(ids)} (unk={n_unk})")
        if not match:
            print(f"         Decoded: {repr(decoded)}")

    print(f"\nAll tests passed: {all_pass}")

    # 全文抽样
    import random
    random.seed(0)
    lines = [l for l in text.split("\n") if l.strip()]
    sample_lines = random.sample(lines, min(100, len(lines)))
    n_fail = 0
    for line in sample_lines:
        ids = tok.encode(line, add_bos=False, add_eos=False)
        decoded = tok.decode(ids)
        if decoded != line.strip():
            n_fail += 1
            if n_fail <= 3:
                print(f"\n  FAIL sample:")
                print(f"    Input:   {repr(line)}")
                print(f"    Decoded: {repr(decoded)}")
    print(f"\nRandom sample round-trip failures: {n_fail}/100")

    sample = text[:100000]
    enc = tok.encode(sample, add_bos=False, add_eos=False)
    print(f"\nCompression: {len(sample)} chars -> {len(enc)} tokens ({len(sample)/len(enc):.2f} chars/token)")
    print(f"UNK count in 100KB sample: {enc.count(UNK_ID)}")


if __name__ == "__main__":
    main()
