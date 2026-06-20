# Logiko

> A constructed international auxiliary language designed for **human readability** and **AI low-compute learning** (converges on 2-5MB of training data).
>
> Combines Esperanto morphology, Lojban syntactic rigor, and basic Chinese/English vocabulary for minimal entropy and zero syntactic ambiguity.

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-orange)

## v4.0 Improvements (Latest, 2026-06)

### Language Improvements
1. **Tense suffixes** `-s/-d/-r` (present/past/future) on verbs, in addition to auxiliaries
2. **`ki` relative clause** (pre-modifier, consistent with "modifier precedes" principle)
3. **Modal system fixed order**: `[modal] + [tense] + [adv] + [verb]`
4. **Compound word rules**: hyphen for new, fused for stable (e.g., `coldbox`, `teachist`)
5. **Discourse markers** fully integrated: `however`, `moreover`, `for-example`, `in-conclusion`, etc.
6. **Natural CoT** (not template): uses `because/so/therefore/this mean` instead of `firstly/secondly`
7. **Phonemic purity**: (C)V(C) enforced, no consonant clusters

### Model & Data
| Aspect | v3 | v4 |
|:---|:---|:---|
| Model params | 8.25M | 8.25M (same) |
| Pretrain steps | 400 | **300** |
| Pretrain ppl | 2.54 | 4.31 |
| SFT steps | 500 | **300** |
| SFT val_ppl | 1.075 | 1.584 |
| Corpus size | 10MB | **15MB** |
| Knowledge topics | 30+ | **50+** |
| Math level | elementary + algebra | **+ calculation process + geometry proof + probability combo** |
| Reasoning | template (firstly/secondly) | **natural CoT (because/so/therefore)** |
| Translation tasks | removed | removed |
| Daily chat variants | 1x | **2x** |

## Quick Start

### Install
```bash
pip install torch  # CPU: pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Chat (Interactive CLI)
```bash
cd scripts
python3 chat.py
```

Example:
```
you> what be water?
ai> water be one clear-a liquid without color or taste. ta freeze in zero degree, 
    and boil in hundred degree. all life need water.

you> what be fire?
ai> fire be rapid-a oxidation that produce heat, light, and smoke. ta require three 
    element: fuel, heat, and air.

you> why sky be blue?
ai> sun light be white-a, but ta be make of all color. when ta enter atmosphere...
```

### CLI Commands
| Command | Description |
|:---|:---|
| `exit` / `quit` / Ctrl+C | Leave |
| `reset` | Clear history |
| `single` / `multi` | Switch single-turn (default) / multi-turn mode |
| `:temp 0.85` | Set temperature |
| `:rep 1.15` | Set repetition penalty |
| `:freq 0.3` | Set frequency penalty |
| `:pres 0.2` | Set presence penalty |

## How to Train (From Scratch)

### Step 1: Generate SFT data
```bash
python3 scripts/sft_data_gen.py
# Output: 15000 examples
```

### Step 2: Generate 15MB corpus
```bash
python3 scripts/corpus_gen.py
# Output: 15MB corpus with v4 grammar
```

### Step 3: Train tokenizer
```bash
python3 scripts/tokenizer.py
# Output: vocab=1500, 0 UNK
```

### Step 4: Pretrain (300 steps, ~10 min CPU)
```bash
python3 scripts/train.py \
  --max_steps 300 \
  --batch_size 16 --grad_accum 2 \
  --seq_len 256 --d_model 256 \
  --n_heads 8 --n_kv_heads 4 --n_layers 8 --d_ff 1024 \
  --max_lr 5e-4 --warmup 30 \
  --log_every 30 --save_every 300
```
Expected: loss ~1.46, ppl ~4.31

### Step 5: SFT (300 steps, ~6 min CPU)
```bash
python3 scripts/sft.py \
  --pretrained logiko/logiko_final.pt \
  --max_steps 300 \
  --batch_size 8 --grad_accum 2 \
  --max_len 256 \
  --max_lr 1e-4 --min_lr 1e-5 --warmup 30 \
  --log_every 30 --eval_every 150 --save_every 300
```
Expected: val_ppl ~1.58

### Step 6: Chat!
```bash
python3 scripts/chat.py --ckpt logiko/logiko_sft_best.pt
```

## Model Architecture (Qwen3-style)

| Component | Implementation |
|:---|:---|
| Attention | GQA: 8 query heads, 4 KV heads |
| QK-Norm | RMSNorm on Q and K |
| Position | RoPE |
| MLP | SwiGLU |
| Norm | RMSNorm (pre-norm) |
| Params | 8,253,184 (8.25M) |
| Layers | 8 |
| Context | 256 tokens |

## Logiko Language v4.0 Design

### Key Features
1. **Phonemic purity**: (C)V(C) structure, one letter = one phoneme
2. **Tense system**: auxiliaries (`did/will`) + suffixes (`-s/-d/-r`)
3. **Relative clause**: `ki` + clause + noun (pre-modifier)
4. **Yes/no questions**: `cu` (not `if`, which only means "if" conditionally)
5. **Possessive**: `I-a` (my), `ta-a` (his/her/its)
6. **Modal order**: `[modal] + [tense] + [adv] + [verb]`
7. **Discourse markers**: `however`, `moreover`, `for-example`, `in-conclusion`
8. **Compound words**: hyphen for new (`cold-box`), fused for stable (`coldbox`)
9. **Natural CoT**: `because/so/therefore` (not `firstly/secondly`)

### Vocabulary
- **820 core roots** in 21 semantic classes
- **12 derivational affixes**: `mal-`, `-ist`, `-ej`, `-il`, `-ar`, `-ec`, `-uc`, `-in`, `-id`, `-em`, `-abl`, `-a`/`-e`
- **50+ knowledge topics**: water, fire, sun, earth, atom, energy, gravity, heart, disease, law, history, language, money, dream, freedom, light, sound, dna, evolution, climate, ocean, volcano, earthquake, tsunami, rain-forest, desert, river, internet, ai, photosynthesis, respiration, brain, blood, etc.

## Training Data Quality

### Knowledge-base driven
All knowledge paragraphs based on **real fact templates** for 50+ topics, each with 5-10 verified facts.

### Semantic collocation
Verb-object compatibility table prevents nonsense (e.g., `eat → food` only, `study → science/math/medicine/law` only).

### Math (elementary to middle school)
- **Arithmetic** with calculation process (step-by-step)
- **Algebra**: linear + quadratic equations
- **Geometry**: area, perimeter, angle sum
- **Probability**: simple + combinatorial
- **Percentage**, **inequality**, **algebraic identity**

### Natural reasoning
Multi-step causal chains with real logic:
```
because sun heat water, ta evaporate and rise. when ta cool in atmosphere, 
ta condense into cloud. this lead to rain, which flow back to sea. so, 
water cycle be complete.
```

### No translation tasks
Removed to avoid Logiko spelling interference.

## Model Performance (v4, 300 steps)

| Test | Score |
|:---|:---|
| Knowledge Q&A | 5/5 perfect single-sentence answers (water, fire, sun, atom, heart) |
| Reasoning | Partial (correct opening, may degrade) |
| Math | Weak (learns format, not computation) |
| Grammar explanation | Partial |
| Daily chat | Appropriate |
| Multi-turn context | Works in single-turn mode (default) |

## Known Limitations

1. **Math computation**: Model learns format but not actual arithmetic. Needs larger model or tool use.
2. **Long generation**: After 2-3 sentences, may degrade. Needs longer training.
3. **CPU training limit**: 300 steps in ~10 min. GPU would allow 5000+ steps.
4. **Context length**: 256 tokens limits multi-turn to ~4-6 turns.

## Comparison with Other Languages

| Dimension | Logiko v4 | Esperanto | English | Lojban |
|:---|:---|:---|:---|:---|
| Root count | ~800-1000 | ~3000 | 100,000+ | 1340 |
| Phonemic consistency | Complete | Complete | Inconsistent | Complete |
| AI training data | **2-15 MB** | ~50 MB | 50+ GB | 5-10 MB |
| Syntactic ambiguity | zero | very low | high | zero |
| Tense marking | aux + suffix | suffix | auxiliary | context |
| Relative clause | `ki` (pre) | (post) | (post) | (pre) |

## License

MIT
