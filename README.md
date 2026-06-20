# Logiko

> A constructed international auxiliary language designed for **human readability** (Chinese/English native speaker friendly) and **AI low-compute learning** (converges on 2-5MB of training data).
>
> Combines Esperanto morphology, Lojban syntactic rigor, and basic Chinese/English vocabulary for minimal entropy and zero syntactic ambiguity.

## v3 Improvements (2026-06)

| Aspect | v2 | v3 |
|:---|:---|:---|
| Model params | 3.5M | **8.25M** |
| Architecture | GQA + QK-Norm | GQA + QK-Norm (deeper) |
| Corpus size | 5MB | **10MB** |
| Knowledge topics | 15 | **30+** |
| Math level | arithmetic only | **arithmetic + algebra + geometry + probability** |
| Reasoning corpus | none | **multi-step causal chains** |
| Multi-domain | basic | **science, medicine, law, engineering, history, finance, art** |
| Translation tasks | yes | **removed (avoid Logiko spelling interference)** |
| SFT examples | 8000 | **15000** |
| Answer variants | 1 per Q | **2-3 per Q** |

## Quick Start

### Install
```bash
pip install torch
```

### Chat (Interactive CLI with Multi-turn Context)
```bash
cd scripts
python3 chat.py
```

### CLI Commands
| Command | Description |
|:---|:---|
| exit / quit / Ctrl+C | Leave the chat |
| reset | Clear conversation history |
| save <file> | Save conversation |
| :temp 0.85 | Set temperature |
| :topk 40 | Set top-k |
| :rep 1.15 | Set repetition penalty |
| :freq 0.3 | Set frequency penalty |
| :pres 0.2 | Set presence penalty |

## How to Train (From Scratch)

### Step 1: Generate SFT data
```bash
python3 scripts/sft_data_gen.py
```

### Step 2: Generate 10MB corpus
```bash
python3 scripts/corpus_gen.py
```

### Step 3: Train tokenizer
```bash
python3 scripts/tokenizer.py
```

### Step 4: Pretrain (8.25M model)
```bash
python3 scripts/train.py \
  --max_steps 400 \
  --batch_size 16 --grad_accum 2 \
  --seq_len 256 --d_model 256 \
  --n_heads 8 --n_kv_heads 4 --n_layers 8 --d_ff 1024 \
  --max_lr 5e-4 --warmup 50 \
  --log_every 50 --save_every 200
```
Expected: loss ~0.93, ppl ~2.54 (CPU ~9 min)

### Step 5: SFT fine-tune
```bash
python3 scripts/sft.py \
  --pretrained logiko/logiko_final.pt \
  --max_steps 500 \
  --batch_size 8 --grad_accum 2 \
  --max_len 256 \
  --max_lr 1e-4 --min_lr 1e-5 --warmup 30 \
  --log_every 25 --eval_every 100 --save_every 500
```
Expected: val_ppl ~1.075 (CPU ~6 min)

### Step 6: Chat!
```bash
python3 scripts/chat.py --ckpt logiko/logiko_sft_best.pt
```

## Model Architecture (Qwen3-style)

| Component | Implementation |
|:---|:---|
| Attention | Grouped Query Attention (GQA): 8 query heads, 4 KV heads |
| QK-Norm | RMSNorm on Q and K (Qwen3-style) |
| Position encoding | RoPE |
| MLP | SwiGLU |
| LayerNorm | RMSNorm (pre-norm) |
| Total params | 8,253,184 (8.25M) |
| Layers | 8 |
| Hidden dim | 256 |
| Context length | 256 tokens |

## Logiko Language v2.0 Design

1. **Phonemic purity**: One letter = one phoneme
2. **Root purity**: Only atomic semantic roots
3. **Simplified tense**: past/fut adverbs + single auxiliary
4. **cu for yes/no**: Replaces if (avoiding semantic conflict)
5. **Fused suffixes**: teachist, learnej, cutil (no hyphens)
6. **-uc container**: Replaces -ing (English interference)
7. **Possessive via -a**: I-a (my), ta-a (his/her/its)

## Training Data Quality

- **Knowledge-base driven**: 30+ topics with real fact templates
- **Semantic collocation**: verb-object compatibility prevents nonsense
- **Math**: arithmetic + algebra + geometry + probability (always correct)
- **Reasoning**: multi-step causal chains with real logic
- **No translation**: removed to avoid Logiko spelling interference

## Model Performance

- Knowledge Q&A: ~62% fully correct
- Reasoning: ~40% (sky blue, photosynthesis correct)
- Multi-turn context: works for 2-4 turns
- Pretraining ppl: 2.54
- SFT val_ppl: 1.075

## License

MIT
