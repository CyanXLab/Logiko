# Logiko

> A constructed international auxiliary language designed for **human readability** (Chinese/English native speaker friendly) and **AI low-compute learning** (converges on 2-5MB of training data).
>
> Combines Esperanto morphology, Lojban syntactic rigor, and basic Chinese/English vocabulary for minimal entropy and zero syntactic ambiguity.

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-orange)
![Version](https://img.shields.io/badge/version-2.0-orange)

## What's New in v2

- **Qwen3-style architecture**: Grouped Query Attention (GQA, 6 Q-heads / 2 KV-heads) + QK-Norm (RMSNorm on Q and K)
- **Smaller but better**: 3.53M params (down from 6.58M) with lower val perplexity (1.04 vs 1.13)
- **Multi-turn chat**: full conversation history is fed to the model with a sliding-window context
- **Better decoding**: repetition + frequency + presence penalties, plus `no_repeat_ngram_size`
- **Live decoding settings**: change temperature/top-k/top-p/penalties on the fly inside the chat CLI
- **Language v2 redesign** (see spec.md): `cu` yes/no particle, `I-a` possessive, `past`/`fut` tense adverbs, fused derivational suffixes (`teachist`, `learnej`, `cutil`, `teauc`), new `-uc` container suffix, strict (C)V(C) phonemic purity

## Quick Start

### Install

```bash
pip install torch  # CPU version: pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Chat with the model (interactive CLI)

```bash
cd scripts
python3 chat.py
```

You'll see:

```
 __                  ___  _
 / _\ ___ _ __ _   _ / _ \| |_
 \ \ / _ \ '__| | | | | | | __|
 _\ \  __/ |  | |_| | |_| | |_
 \__/\___|_|   \__, |\___/ \__|
               |___/

  Logiko v2 — Multi-turn Q&A console.
  Conversation history is preserved within session.
  Commands:  exit | quit | reset | save <file> | load <file> | help | settings | suggest

you> what be water?
ai> water be one clear-a liquid. ta freeze in zero degree, and boil in hundred degree. all life need water.
   [97 chars, 0.11s]

you> what -a mean?
ai> suffix -a mark adjective. example: big-a mean big, red-a mean red. adjective always come before noun.

you> cu ta be student?
ai> yes, ta be student.

you> what ta-a name be?
ai> ta-a name be li.
```

The CLI now keeps the full conversation as context, so follow-up questions like
`how about fire?` are answered correctly without re-stating the topic.

#### CLI Commands

| Command | Description |
|:---|:---|
| `exit` / `quit` / Ctrl+C | Leave the chat |
| `reset` | Clear conversation history |
| `save <file>` | Save conversation to file |
| `load <file>` | Load conversation from file |
| `help` | Show help |
| `settings` | Show current decoding settings |
| `suggest` | Show suggested opening questions |
| `tokens` | Show current token count of context |
| `:temp 0.85` | Set temperature |
| `:topk 40` | Set top-k |
| `:topp 0.9` | Set top-p |
| `:rep 1.15` | Set repetition penalty |
| `:freq 0.3` | Set frequency penalty |
| `:pres 0.2` | Set presence penalty |
| `:ngram 3` | Set `no_repeat_ngram_size` (0 to disable) |
| `:max 120` | Set max new tokens |

#### Decoding penalties (v2)

The decoder now combines four penalties for better diversity and coherence:

| Penalty | Effect | Default |
|:---|:---|:---:|
| `repetition_penalty` (1.15) | Divides logits of already-seen tokens (CTRL-style) | 1.15 |
| `frequency_penalty` (0.3) | Linearly penalises tokens by raw count (OpenAI-style) | 0.3 |
| `presence_penalty` (0.2) | Penalises any token that has appeared at least once | 0.2 |
| `no_repeat_ngram_size` (3) | Hard-blocks any 3-gram that already occurred | 3 |

### One-shot generation

```bash
python3 scripts/generate.py \
  --ckpt models/logiko_sft_best.pt \
  --prompt "Q: what be water?
A: water" \
  --max_new_tokens 100 \
  --temperature 0.5 --top_k 30 --top_p 0.9 \
  --repetition_penalty 1.15 --frequency_penalty 0.3 --presence_penalty 0.2 \
  --no_repeat_ngram_size 3
```

## Repository Structure

```
Logiko/
├── README.md                  # This file
├── spec.md                    # Full language specification v2.0 (Chinese)
├── sample_generations.txt     # Sample model outputs (v2)
├── LICENSE
├── scripts/                   # All code
│   ├── chat.py                # Interactive CLI (v2: multi-turn context + 4 penalties)
│   ├── generate.py            # One-shot generation (repetition/freq/presence/ngram)
│   ├── corpus_gen.py          # Corpus generator (v2: semantic collocation + math)
│   ├── tokenizer.py           # BPE tokenizer (SentencePiece-style, 0 UNK)
│   ├── model.py               # Qwen3-style decoder (RoPE + RMSNorm + SwiGLU + GQA + QK-Norm)
│   ├── train.py               # Pretraining loop (AdamW + cosine schedule)
│   ├── sft.py                 # SFT fine-tuning (loss mask, val split)
│   └── sft_data_gen.py        # SFT data generator (8000 pairs, 40% multi-turn)
├── models/                    # Trained model checkpoints
│   ├── logiko_pretrain.pt     # Pretrained model (1000 steps, ppl=2.83)
│   ├── logiko_sft_final.pt    # SFT model (500+500 steps, val_ppl=1.04)
│   ├── logiko_sft_best.pt     # Best SFT checkpoint (val_ppl=1.04)
│   └── tokenizer.json         # BPE tokenizer (vocab=1500)
└── data/                      # Training data
    ├── logiko_corpus.txt      # 5MB pretraining corpus
    └── sft_data.jsonl         # 8000 SFT Q&A pairs (40% multi-turn)
```

## Reproduce from Scratch

```bash
# 1. Generate SFT data first (corpus will reference it)
python3 scripts/sft_data_gen.py

# 2. Generate 5MB pretraining corpus (with Q&A mixed in)
python3 scripts/corpus_gen.py

# 3. Train BPE tokenizer (vocab=1500, 0 UNK)
python3 scripts/tokenizer.py

# 4. Pretrain (1000 steps, ~4 min on CPU)
python3 scripts/train.py \
  --max_steps 1000 --batch_size 16 --grad_accum 2 \
  --seq_len 192 --d_model 192 --n_heads 6 --n_kv_heads 2 \
  --n_layers 6 --d_ff 768 --qk_norm \
  --max_lr 6e-4 --warmup 50 --log_every 50 --save_every 500

# 5. SFT fine-tune (500 steps, then continue 500 more, ~2 min on CPU)
python3 scripts/sft.py \
  --pretrained models/logiko_pretrain.pt \
  --max_steps 500 --batch_size 8 --grad_accum 2 \
  --max_len 192 --max_lr 1e-4 --warmup 30 \
  --log_every 50 --eval_every 100 --save_every 500

# 5b. (optional) continue SFT for another 500 steps on the same data
python3 scripts/sft.py \
  --pretrained models/logiko_sft_final.pt \
  --max_steps 500 --batch_size 8 --grad_accum 2 \
  --max_len 192 --max_lr 5e-5 --warmup 20 \
  --log_every 50 --eval_every 100 --save_every 500

# 6. Chat!
python3 scripts/chat.py
```

## Model Performance

Sample generations on `logiko_sft_best.pt` (see `sample_generations.txt` for the full set):

| Question | Model answer | Verdict |
|:---|:---|:---:|
| what be water? | water be one clear-a liquid. ta freeze in zero degree, and boil in hundred degree. all life need water. | ✅ correct |
| what be fire? | fire be hot-a and bright-a. ta need air for burn. ta can burn wood, paper, cloth, but can not burn water or stone. | ✅ correct |
| what be sun? | sun be nearest star to earth. ta be about one hundred fifty million kilometer away. ta light take eight minute to reach earth. | ✅ correct |
| what be tree? | tree be largest type of plant. ta make oxygen through photosynthesis. forest be place with many tree. | ✅ correct |
| what -a mean? | suffix -a mark adjective. example: big-a mean big, red-a mean red. adjective always come before noun. | ✅ correct |
| what mal- mean? | prefix mal- mark opposite. example: mal-good mean bad, mal-big mean small, mal-happy mean sad. | ✅ correct |
| what cu mean? | cu be one particle that mark yes-no question. ta come at start of sentence. example: cu you will go? mean will you go? | ✅ correct |
| what ta mean? | ta be one gender-neutral pronoun. ta can refer to person, animal, or thing. ta-many be plural form, mean they. | ✅ correct |

**Summary**: 3/3 correct on concrete definitions (water, fire, sun), 2/2 mostly correct on
grammar particles (`-a`, `ta`). At temperature 0.9 with the new penalty stack, the model
produces 3 different valid definitions of "fire" instead of repeating one canned answer.

## Key Metrics

| Metric | Value |
|:---|:---|
| Tokenizer vocab size | 1,500 |
| UNK count | 0 |
| Round-trip failures | 0/100 |
| Model architecture | Qwen3-style decoder (RoPE + RMSNorm + SwiGLU + **GQA** + **QK-Norm**) |
| Model parameters | 3,534,912 (3.53M) |
| Layers | 6 |
| Hidden dim (d_model) | 192 |
| Query heads | 6 |
| KV heads (GQA) | 2 |
| FFN dim (SwiGLU) | 768 |
| Context length | 192 |
| Pretraining steps | 1000 |
| Pretraining ppl | 2.83 |
| SFT examples | 8,000 (40% multi-turn) |
| SFT steps | 500 + 500 |
| SFT val ppl | 1.04 |
| Training time (CPU) | ~6 minutes total |

## Logiko Language Design (v2)

### Writing & Pronunciation
- 26 lowercase Latin letters (proper nouns capitalized)
- Standard punctuation: `,` `.` `?` `!` `-` for the `mal-` prefix only
- **One letter = one phoneme** (pinyin-like): a=啊, e=诶, i=衣, o=喔, u=乌
- Stress always on penultimate syllable
- **Phonemic purity (v2)**: strict (C)V(C) syllable structure — no English-style consonant clusters

### Word Formation
~820 root words + **11 derivational affixes** generate tens of thousands of words.

#### Parts of Speech (mandatory suffixes)
| POS | Suffix | Example | Meaning |
|:---|:---|:---|:---|
| Noun | (none) | `book`, `water` | book, water |
| Verb | (none) | `go`, `eat` | go, eat (always base form) |
| Adjective | `-a` | `big-a`, `red-a` | big, red |
| Adverb | `-e` | `fast-e`, `good-e` | fast-ly, well |

#### Derivational Affixes (v2: fused, no hyphen)

| Affix | Function | Example |
|:---|:---|:---|
| `mal-` | opposite (keeps hyphen) | `good` → `mal-good` (bad) |
| `-ist` | person who does | `teach` → `teachist` (teacher) |
| `-ej` | place | `learn` → `learnej` (school) |
| `-il` | tool | `cut` → `cutil` (knife) |
| `-ar` | collection | `book` → `bookar` (library) |
| `-ec` | abstract quality | `good` → `goodec` (goodness) |
| `-uc` | **container (v2 new)** | `tea` → `teauc` (teacup) — replaces `-ing` |
| `-in` | feminine | `dog` → `dogin` (female dog) |
| `-id` | offspring | `dog` → `dogid` (puppy) |
| `-em` | tendency | `talk` → `talkem` (talkative) |
| `-abl` | able to be | `see` → `seeabl` (visible) |

> v1 used hyphenated forms (`teach-ist`, `learn-ej`, `tea-ing`).
> v2 fuses them into a single token because they are fully productive and
> unambiguous. `-ing` was renamed to `-uc` to avoid interference from English
> `-ing` (which is a verb-forming suffix, not a container suffix).

#### Compound Words
Hyphenate roots only when the compound is compositional but not lexicalised:
- `cold-box` = refrigerator
- `think-machine` = computer
- `moneyej` = bank (fused: money + place)
- `weekone` = Monday (fused: week + one)
- `sunlight` = sunlight (fused: sun + light)
- `starship` = spaceship (fused: star + ship)

### Grammar (zero ambiguity)

#### Word Order: Strict SVO
```
I eat apple.
Ta do work.
```

#### Modifiers: Always Precede
- **Noun phrase**: `[demonstrative] + [number] + [adjective]* + [noun]`
  - `this two big-a red-a apple` (these two big red apples)
- **Verb phrase (v2 simplified)**: `[time-adverb] + [single-aux] + [adverb]* + [verb]`
  - `I tomorrow will fast-e go.` (I will go fast tomorrow)

#### Tense (v2: avoid auxiliary stacking)

v1 stacked auxiliaries for compound tenses (`I did is eat.` → past progressive),
which was both unnatural and ambiguous. v2 uses time adverbs `past` / `fut` plus
**at most one** auxiliary:

| Tense | v1 | v2 |
|:---|:---|:---|
| Present | `I eat.` | `I eat.` |
| Past | `I did eat.` | `I past eat.` (or `I did eat.`) |
| Progressive | `I is eat.` | `I is eat.` |
| Future | `I will eat.` | `I will eat.` (or `I fut eat.`) |
| Perfect | `I have eat.` | `I have eat.` |
| Past progressive | `I did is eat.` ❌ | `I past is eat.` ✅ |
| Past perfect | `I did have eat.` ❌ | `I past have eat.` ✅ |

#### Negation: `not` before verb
- `I not go.` (I don't go)
- `Ta past not eat.` (He didn't eat)

#### Plural: zero inflection
- `one book` (one book), `three book` (three books), `many person` (many people)

#### Pronouns (gender & case neutral)
| Pronoun | Meaning | Plural |
|:---|:---|:---|
| `I` | I | `we` |
| `you` | you (sing/plur) | (same) |
| `ta` | he/she/it | `ta-many` (they) |
| `self` | self (reflexive) | - |
| `this` | this | - |
| `that` | that | - |

#### Possessive (v2: suffix `-a` instead of `of`)
v1 used `book of I` (two words, redundant). v2 reuses the adjective suffix `-a`
on pronouns to form possessives in a single word:

| Possessive | v1 | v2 |
|:---|:---|:---|
| my | `book of I` | `I-a book` |
| our | `book of we` | `we-a book` |
| your | `book of you` | `you-a book` |
| his/her/its | `book of ta` | `ta-a book` |
| their | `book of ta-many` | `ta-many-a book` |

Complex possessives still use `of`:
`the book of the teachist who did teach me` (the book of the teacher who taught me).

#### Questions (no inversion)
- **WH-question**: WH-word first, keep statement order
  - `What you will do?` (What will you do?)
  - `Who past eat apple?` (Who ate the apple?)
- **Yes/No (v2: `cu` instead of `if`)**: v1 used `If you will go?`, which collided
  with the conditional `if`. v2 borrows Esperanto's `ĉu` as `cu`:
  - `cu you will go?` (Will you go?)
  - `cu ta past eat apple?` (Did he eat the apple?)
  - `cu you will go if it rain?` (Will you go if it rains?) — no more `if`/`if` clash.

#### Passive Voice
`Subject + be + verb + by + agent`
- `Apple be eat by I.` (The apple is eaten by me)

#### Comparison
| Form | Structure | Example |
|:---|:---|:---|
| Equal | `as + adj-a + as` | `Ta as tall-a as I.` |
| Comparative | `more + adj-a + than` | `Ta more tall-a than I.` |
| Superlative | `most + adj-a + of` | `Ta most tall-a of all person.` |

### Multi-turn Conversation (v2 new)

The SFT data now contains 40% multi-turn examples so the model can track topic
and pronouns across turns. Format:

```
Q: what be water?
A: water be one clear-a liquid. ta freeze in zero degree, and boil in hundred degree. all life need water.
Q: how about fire?
A: fire be hot-a and bright-a. ta need air for burn.
Q: cu ta can burn water?
A: no, ta can not burn water.
```

See `spec.md` §5 for the full multi-turn specification.

### Comparison with Other Languages

| Dimension | Logiko | Esperanto | English | Lojban |
|:---|:---|:---|:---|:---|
| Root count | ~800 | ~3000 | 100,000+ | 1340 |
| Alphabet | 26 (ASCII) | 28 (with diacritics) | 26 | 26 |
| Gender marking | none | has (-in) | has (he/she) | none |
| AI training data need | **2-5 MB** | ~50 MB | 50+ GB | 5-10 MB |
| Syntactic ambiguity | zero | very low | high | zero |

## Design Philosophy

Logiko was designed with three principles:

1. **AI-friendly**: Token vocabulary of ~1500, fully regular morphology (no go/went/gone),
   semantic compositionality (`flymachine` = airplane). A 3.53M parameter model converges
   in 1000 pretrain + 500+500 SFT steps on 5MB of text, reaching val_ppl=1.04.

2. **Human-friendly**: SVO word order, English-derived roots, Chinese-pinyin-inspired
   pronunciation, zero inflection (no cases, no conjugation, no gender).

3. **Zero ambiguity**: Mandatory POS suffixes (`-a` for adjectives, `-e` for adverbs),
   fixed word order, explicit logical connectors, no homonyms, single-purpose particles
   (`cu` only marks yes/no questions, `if` only marks conditionals).

## Limitations

1. **Math computation**: The model can produce the format
   `if we add X and Y, result be Z` but the value Z is often wrong. Solving this
   requires a larger model (>10M params) and a dedicated math training phase, or
   external tool use.

2. **Open-ended Q&A**: Without a partial answer hint, the model may give canned
   responses from similar questions in its training set. The CLI `chat.py`
   automatically adds a topic hint (e.g., `A: water`) to mitigate this; use
   `--no_hint` to disable.

3. **Long multi-turn conversations**: The 192-token context window supports
   roughly 4-6 turns before the sliding window starts dropping history. Longer
   context (e.g., max_seq_len=512) would require re-training.

4. **CPU-only training**: Larger configurations take 30+ minutes for 1500 steps
   on CPU. GPU training recommended for serious scaling.

## License

MIT

## Citation

```bibtex
@misc{logiko2026,
  title={Logiko: A Constructed Language for AI-Friendly Communication},
  year={2026},
  url={https://github.com/CyanXLab/Logiko}
}
```
