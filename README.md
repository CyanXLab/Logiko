# Logiko

> A constructed international auxiliary language designed for **human readability** (Chinese/English native speaker friendly) and **AI low-compute learning** (converges on 2-5MB of training data).
>
> Combines Esperanto morphology, Lojban syntactic rigor, and basic Chinese/English vocabulary for minimal entropy and zero syntactic ambiguity.

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-orange)

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

  Logiko interactive Q&A console.

you> what be water?
ai> water be one clear-a liquid. ta freeze in zero degree, and boil in hundred degree. all life need water.
   [97 chars, 0.11s]

you> what be fire?
ai> fire be hot-a and bright-a. ta need air for burn. ta can burn wood and paper, but can not burn water or stone.

you> what -a mean?
ai> suffix -a mark adjective. example: big-a mean big, red-a mean red. adjective always come before noun.

you> what ta mean?
ai> ta be third-person pronoun, mean he, she, or it. ta-many mean they.

you> how say I love you in logiko?
ai> I love you in logiko be: I love you.
```

#### CLI Commands

| Command | Description |
|:---|:---|
| `exit` / `quit` / Ctrl+C | Leave the chat |
| `reset` | Clear conversation history |
| `save <file>` | Save conversation to file |
| `help` | Show help |
| `settings` | Show current decoding settings |
| `suggest` | Show suggested questions |
| `:temp 0.5` | Set temperature |
| `:topk 30` | Set top-k |
| `:topp 0.9` | Set top-p |
| `:rep 1.15` | Set repetition penalty |
| `:max 80` | Set max new tokens |

### One-shot generation

```bash
python3 scripts/generate.py \
  --ckpt models/logiko_sft_final.pt \
  --prompt "Q: what be water?
A: water" \
  --max_new_tokens 80 \
  --temperature 0.4 --top_k 30 --top_p 0.9 --repetition_penalty 1.15
```

## Repository Structure

```
Logiko/
├── README.md                  # This file
├── spec.md                    # Full language specification
├── sample_generations.txt     # Sample model outputs
├── scripts/                   # All code
│   ├── chat.py                # Interactive CLI chat loop
│   ├── generate.py            # One-shot generation (with repetition penalty)
│   ├── corpus_gen.py          # Corpus generator (v2: semantic collocation + correct math)
│   ├── tokenizer.py           # BPE tokenizer v6 (SentencePiece-style, 0 UNK)
│   ├── model.py               # GPT/Qwen-style decoder (RoPE + RMSNorm + SwiGLU + MHA)
│   ├── train.py               # Pretraining loop (AdamW + cosine schedule)
│   ├── sft.py                 # SFT fine-tuning (loss mask, val split)
│   └── sft_data_gen.py        # SFT data generator (8000 Q&A pairs)
├── models/                    # Trained model checkpoints
│   ├── logiko_pretrain.pt     # Pretrained model (800 steps, ppl=4.86)
│   ├── logiko_sft_final.pt    # SFT model (800 steps, val_ppl=1.13)
│   ├── logiko_sft_best.pt     # Best SFT checkpoint
│   └── tokenizer.json         # BPE tokenizer (vocab=1500)
└── data/                      # Training data
    ├── logiko_corpus.txt      # 5MB pretraining corpus
    └── sft_data.jsonl         # 8000 SFT Q&A pairs
```

## Reproduce from Scratch

```bash
# 1. Generate SFT data first (corpus will reference it)
python3 scripts/sft_data_gen.py

# 2. Generate 5MB pretraining corpus (with Q&A mixed in)
python3 scripts/corpus_gen.py

# 3. Train BPE tokenizer (vocab=1500, 0 UNK)
python3 scripts/tokenizer.py

# 4. Pretrain (800 steps, ~2 min on CPU)
python3 scripts/train.py \
  --max_steps 800 --batch_size 32 --grad_accum 1 \
  --seq_len 128 --d_model 128 --n_heads 4 --n_layers 4 --d_ff 512 \
  --max_lr 5e-4 --warmup 30 --log_every 50 --save_every 400

# 5. SFT fine-tune (800 steps, ~1.5 min on CPU)
python3 scripts/sft.py \
  --pretrained logiko/logiko_final.pt \
  --max_steps 800 --batch_size 8 --grad_accum 2 \
  --max_len 128 --max_lr 1e-4 --warmup 30 \
  --log_every 50 --eval_every 200 --save_every 800

# 6. Chat!
python3 scripts/chat.py
```

## Model Performance

After SFT, the model correctly answers 13/14 knowledge questions:

| Question | Answer | Correct? |
|:---|:---|:---:|
| what be water? | water be one clear-a liquid. ta freeze in zero degree, and boil in hundred degree. all life need water. | ✅ |
| what be fire? | fire be hot-a and bright-a. ta need air for burn. ta can burn wood and paper, but can not burn water or stone. | ✅ |
| what be sun? | sun be one star. ta give light and warm to earth. ta rise in east and set in west. | ✅ |
| what be tree? | tree be one plant. ta have root, trunk, branch, leaf. ta can live many year. ta give fruit, wood, and shadow. | ✅ |
| what be person? | person be one animal that can think and speak. ta have head, body, two arm, two leg. ta can make tool and build house. | ✅ |
| what be music? | music be art of sound. person make music with voice or instrument. music can make person feel happy or sad. | ✅ |
| what be season? | year have four season: spring, summer, autumn, winter. in spring, plant grow. in summer, weather be hot-a. | ✅ |
| what be book? | book be many paper with word, bind together. | ✅ |
| what be food? | food give energy to body. person need food for live. bread, rice, meat, vegetable be common-a food. | ✅ |
| what -a mean? | suffix -a mark adjective. example: big-a mean big, red-a mean red. adjective always come before noun. | ✅ |
| what mal- mean? | prefix mal- mark opposite. example: mal-good mean bad, mal-big mean small, mal-happy mean sad. | ✅ |
| what ta mean? | ta be third-person pronoun, mean he, she, or it. ta-many mean they. | ✅ |
| how say I love you in logiko? | I love you in logiko be: I love you. | ✅ |
| how form question? | do what you want talk about? | ❌ |

## Key Metrics

| Metric | Value |
|:---|:---|
| Tokenizer vocab size | 1,500 |
| UNK count | 0 |
| Round-trip failures | 0/100 |
| Model architecture | GPT/Qwen-style decoder (RoPE + RMSNorm + SwiGLU + MHA) |
| Model parameters | 1,241,728 (1.24M) |
| Layers | 4 |
| Hidden dim | 128 |
| Attention heads | 4 |
| Context length | 128 |
| Pretraining steps | 800 |
| Pretraining ppl | 4.86 |
| SFT examples | 8,000 |
| SFT steps | 800 |
| SFT val ppl | 1.13 |
| Knowledge Q&A accuracy | 93% (13/14) |
| Training time (CPU) | ~3 minutes total |

## Logiko Language Design

### Writing & Pronunciation
- 26 lowercase Latin letters (proper nouns capitalized)
- Standard punctuation: `,` `.` `?` `!` `-` for compound words
- Fixed vowel pronunciation (pinyin-like): a=啊, e=诶, i=衣, o=喔, u=乌
- Stress always on penultimate syllable

### Word Formation
**820 root words** + **12 derivational affixes** generate tens of thousands of words.

#### Parts of Speech (mandatory suffixes)
| POS | Suffix | Example | Meaning |
|:---|:---|:---|:---|
| Noun | (none) | `book`, `water` | book, water |
| Verb | (none) | `go`, `eat` | go, eat (always base form) |
| Adjective | `-a` | `big-a`, `red-a` | big, red |
| Adverb | `-e` | `fast-e`, `good-e` | fast-ly, well |

#### Derivational Affixes
| Affix | Function | Example |
|:---|:---|:---|
| `mal-` | opposite | `good` → `mal-good` (bad) |
| `-ist` | person who does | `teach` → `teach-ist` (teacher) |
| `-ej` | place | `learn` → `learn-ej` (school) |
| `-il` | tool | `cut` → `cut-il` (knife) |
| `-ar` | collection | `book` → `book-ar` (library) |
| `-ec` | abstract quality | `good` → `good-ec` (goodness) |
| `-ad` | continued action | `study` → `study-ad` (studying) |
| `-ing` | container | `tea` → `tea-ing` (teacup) |
| `-in` | feminine | `dog` → `dog-in` (female dog) |
| `-id` | offspring | `dog` → `dog-id` (puppy) |
| `-em` | tendency | `talk` → `talk-em` (talkative) |
| `-abl` | able to be | `see` → `see-abl` (visible) |

#### Compound Words
Hyphenate roots directly; meaning = literal sum:
- `cold-box` = refrigerator
- `think-machine` = computer
- `money-ej` = bank
- `week-one` = Monday
- `sun-light` = sunlight
- `star-ship` = spaceship

### Grammar (zero ambiguity)

#### Word Order: Strict SVO
```
I eat apple.
Ta do work.
```

#### Modifiers: Always Precede
- **Noun phrase**: `[demonstrative] + [number] + [adjective]* + [noun]`
  - `this two big-a red-a apple` (these two big red apples)
- **Verb phrase**: `[time] + [aux] + [adverb]* + [verb]`
  - `I tomorrow will fast-e go.` (I will go fast tomorrow)

#### Tense (auxiliary before verb, verb stays base form)
| Tense | Aux | Example |
|:---|:---|:---|
| Past | `did` | `I did go.` (I went) |
| Progressive | `is` | `Ta is eat.` (He is eating) |
| Future | `will` | `We will see.` (We will see) |
| Perfect | `have` | `I have do work.` (I have done the work) |

#### Negation: `not` before verb
- `I not go.` (I don't go)
- `Ta not did eat.` (He didn't eat)

#### Plural: zero inflection
- `one book` (one book), `three book` (three books), `many person` (many people)

#### Pronouns (gender & case neutral)
| Pronoun | Meaning | Plural |
|:---|:---|:---|
| `I` | I | `we` |
| `you` | you (sing/plur) | (same) |
| `ta` | he/she/it | `ta-many` (they) |
| `self` | self (reflexive) | - |

Possessive via `of`: `book of I` (my book)

#### Questions (no inversion)
- **WH-question**: WH-word first, keep statement order
  - `What you will do?` (What will you do?)
  - `Who did eat apple?` (Who ate the apple?)
- **Yes/No**: prefix `if`
  - `If you will go?` (Will you go?)

#### Passive Voice
`Subject + be + verb + by + agent`
- `Apple be eat by I.` (The apple is eaten by me)

#### Comparison
| Form | Structure | Example |
|:---|:---|:---|
| Equal | `as + adj-a + as` | `Ta as tall-a as I.` |
| Comparative | `more + adj-a + than` | `Ta more tall-a than I.` |
| Superlative | `most + adj-a + of` | `Ta most tall-a of all person.` |

### Comparison with Other Languages

| Dimension | Logiko | Esperanto | English | Lojban |
|:---|:---|:---|:---|:---|
| Root count | ~800-1000 | ~3000 | 100,000+ | 1340 |
| Alphabet | 26 (ASCII) | 28 (with diacritics) | 26 | 26 |
| Gender marking | none | has (-ino) | has (he/she) | none |
| AI training data need | **2-5 MB** | ~50 MB | 50+ GB | 5-10 MB |
| Syntactic ambiguity | zero | very low | high | zero |

## Design Philosophy

Logiko was designed with three principles:

1. **AI-friendly**: Token vocabulary of ~1100, fully regular morphology (no go/went/gone), semantic compositionality (`fly-machine` = airplane). A 1.24M parameter model converges in 800 steps on 5MB of text.

2. **Human-friendly**: SVO word order, English-derived roots, Chinese-pinyin-inspired pronunciation, zero inflection (no cases, no conjugation, no gender).

3. **Zero ambiguity**: Mandatory POS suffixes (`-a` for adjectives, `-e` for adverbs), fixed word order, explicit logical connectors, no homonyms.

## Limitations

1. **Math computation**: Model has not learned arithmetic; it can produce the format `if we add X and Y, result be Z` but the value Z is often wrong. Solving this requires a larger model (>10M params) and a dedicated math training phase, or external tool use.

2. **Open-ended Q&A**: Without a partial answer hint, the model may give canned responses from similar questions in its training set. The CLI `chat.py` automatically adds a topic hint (e.g., `A: water`) to mitigate this.

3. **Model capacity**: 1.24M parameters is small for 8000 SFT examples. Scaling to 10M+ parameters (e.g., `d_model=256, n_layers=8`) would significantly improve generalization.

4. **CPU-only training**: Larger models (6.68M) take 30+ minutes for 1500 steps on CPU. GPU training recommended for serious use.

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
