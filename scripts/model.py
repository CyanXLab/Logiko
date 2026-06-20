#!/usr/bin/env python3
"""
Logiko Language Model
=====================
GPT/Qwen-style decoder-only transformer:
  - RMSNorm (pre-norm)
  - Multi-Head Self-Attention with RoPE
  - SwiGLU MLP
  - No biases (per modern convention)
  - Learned positional embeddings disabled (uses RoPE)
"""
import math
import os
import json
from dataclasses import dataclass
from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class ModelConfig:
    vocab_size: int = 1100
    d_model: int = 256          # embedding / hidden dim
    n_heads: int = 8            # attention heads
    n_layers: int = 6           # transformer blocks
    d_ff: int = 1024            # SwiGLU intermediate (will be rounded to multiple of 2/3)
    max_seq_len: int = 512      # context window
    rope_base: float = 10000.0  # RoPE theta
    dropout: float = 0.0        # dropout prob
    tie_embeddings: bool = True # tie LM head with embedding
    pad_id: int = 0

    def __post_init__(self):
        # SwiGLU: hidden dim should be ~2/3 * 4 * d_model per LLaMA convention
        # but here we let user specify directly; round to nearest 2 multiple
        if self.d_ff % 2 != 0:
            self.d_ff += 1


class RMSNorm(nn.Module):
    """Root Mean Square LayerNorm (no bias, no mean subtraction)"""

    def __init__(self, d: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(d))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        norm = torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True) + self.eps)
        return x * norm * self.weight


def precompute_rope(d_head: int, max_seq_len: int, base: float = 10000.0, device=None) -> torch.Tensor:
    """Precompute RoPE rotation matrices.
    Returns: cos, sin of shape (max_seq_len, d_head)
    """
    half = d_head // 2
    freqs = 1.0 / (base ** (torch.arange(0, half, device=device).float() / half))
    t = torch.arange(max_seq_len, device=device).float()
    angles = torch.outer(t, freqs)  # (seq, half)
    cos = torch.cat([angles.cos(), angles.cos()], dim=-1)  # (seq, d_head)
    sin = torch.cat([angles.sin(), angles.sin()], dim=-1)
    return cos, sin


def apply_rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
    """Apply RoPE to x of shape (B, H, T, D).
    cos, sin: (T, D)
    """
    T = x.size(-2)
    cos = cos[:T].unsqueeze(0).unsqueeze(0)  # (1, 1, T, D)
    sin = sin[:T].unsqueeze(0).unsqueeze(0)
    # rotate_half: [x1, x2] -> [-x2, x1]
    x1 = x[..., : x.size(-1) // 2]
    x2 = x[..., x.size(-1) // 2 :]
    rotated = torch.cat([-x2, x1], dim=-1)
    return x * cos + rotated * sin


class Attention(nn.Module):
    """Multi-Head Self-Attention with RoPE, no bias, causal mask."""

    def __init__(self, cfg: ModelConfig):
        super().__init__()
        assert cfg.d_model % cfg.n_heads == 0
        self.n_heads = cfg.n_heads
        self.d_head = cfg.d_model // cfg.n_heads
        self.qkv = nn.Linear(cfg.d_model, 3 * cfg.d_model, bias=False)
        self.proj = nn.Linear(cfg.d_model, cfg.d_model, bias=False)
        self.dropout = cfg.dropout
        # register rope buffers (filled at forward time when device known)
        self.register_buffer("rope_cos", torch.zeros(cfg.max_seq_len, self.d_head), persistent=False)
        self.register_buffer("rope_sin", torch.zeros(cfg.max_seq_len, self.d_head), persistent=False)
        self._rope_init = False

    def _init_rope(self, device):
        cos, sin = precompute_rope(self.d_head, self.rope_cos.size(0), device=device)
        self.rope_cos.copy_(cos)
        self.rope_sin.copy_(sin)
        self._rope_init = True

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.shape
        if not self._rope_init:
            self._init_rope(x.device)
        qkv = self.qkv(x)
        q, k, v = qkv.chunk(3, dim=-1)
        # reshape to (B, H, T, D)
        q = q.view(B, T, self.n_heads, self.d_head).transpose(1, 2)
        k = k.view(B, T, self.n_heads, self.d_head).transpose(1, 2)
        v = v.view(B, T, self.n_heads, self.d_head).transpose(1, 2)
        # RoPE
        q = apply_rope(q, self.rope_cos, self.rope_sin)
        k = apply_rope(k, self.rope_cos, self.rope_sin)
        # scaled dot-product attention (PyTorch 2.0+ flash path)
        out = F.scaled_dot_product_attention(
            q, k, v,
            dropout_p=self.dropout if self.training else 0.0,
            is_causal=True,
        )
        # (B, H, T, D) -> (B, T, C)
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.proj(out)


class SwiGLU(nn.Module):
    """SwiGLU MLP: out = (silu(x @ w1) * (x @ w3)) @ w2"""

    def __init__(self, d_model: int, d_ff: int, dropout: float = 0.0):
        super().__init__()
        # d_ff is the intermediate dim; we project to 2*d_ff because we need w1 and w3 outputs
        self.w_gate = nn.Linear(d_model, d_ff, bias=False)
        self.w_up = nn.Linear(d_model, d_ff, bias=False)
        self.w_down = nn.Linear(d_ff, d_model, bias=False)
        self.dropout = dropout

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        g = F.silu(self.w_gate(x))
        u = self.w_up(x)
        return self.w_down(F.dropout(g * u, p=self.dropout, training=self.training))


class TransformerBlock(nn.Module):
    """Pre-norm transformer block: Attention + SwiGLU with residual connections."""

    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.norm1 = RMSNorm(cfg.d_model)
        self.attn = Attention(cfg)
        self.norm2 = RMSNorm(cfg.d_model)
        self.mlp = SwiGLU(cfg.d_model, cfg.d_ff, dropout=cfg.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.norm1(x))
        x = x + self.mlp(self.norm2(x))
        return x


class LogikoLM(nn.Module):
    """GPT-style decoder-only LM."""

    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.cfg = cfg
        self.token_embed = nn.Embedding(cfg.vocab_size, cfg.d_model, padding_idx=cfg.pad_id)
        self.blocks = nn.ModuleList([TransformerBlock(cfg) for _ in range(cfg.n_layers)])
        self.norm_f = RMSNorm(cfg.d_model)
        if cfg.tie_embeddings:
            self.lm_head = nn.Linear(cfg.d_model, cfg.vocab_size, bias=False)
            self.lm_head.weight = self.token_embed.weight  # tie
        else:
            self.lm_head = nn.Linear(cfg.d_model, cfg.vocab_size, bias=False)
        # init
        self.apply(self._init_weights)

    @staticmethod
    def _init_weights(module):
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.padding_idx is not None:
                module.weight.data[module.padding_idx].zero_()

    def forward(self, idx: torch.Tensor, targets: Optional[torch.Tensor] = None):
        """
        idx: (B, T) long
        targets: (B, T) long, optional
        returns: logits (B, T, V), loss (scalar) if targets given
        """
        x = self.token_embed(idx)  # (B, T, C)
        for block in self.blocks:
            x = block(x)
        x = self.norm_f(x)
        logits = self.lm_head(x)  # (B, T, V)
        loss = None
        if targets is not None:
            loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)),
                targets.view(-1),
                ignore_index=-100,
            )
        return logits, loss

    def num_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())

    def num_trainable_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def build_model(
    vocab_size: int = 1100,
    d_model: int = 256,
    n_heads: int = 8,
    n_layers: int = 6,
    d_ff: int = 1024,
    max_seq_len: int = 512,
) -> LogikoLM:
    cfg = ModelConfig(
        vocab_size=vocab_size,
        d_model=d_model,
        n_heads=n_heads,
        n_layers=n_layers,
        d_ff=d_ff,
        max_seq_len=max_seq_len,
    )
    return LogikoLM(cfg)


def save_model(model: LogikoLM, path: str, extra: dict = None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "model_state": model.state_dict(),
        "config": model.cfg.__dict__,
    }
    if extra:
        payload["extra"] = extra
    torch.save(payload, path)
    print(f"Model saved to {path}")


def load_model(path: str, map_location="cpu") -> Tuple[LogikoLM, dict]:
    payload = torch.load(path, map_location=map_location, weights_only=False)
    cfg = ModelConfig(**payload["config"])
    model = LogikoLM(cfg)
    model.load_state_dict(payload["model_state"])
    return model, payload.get("extra", {})


def main():
    """Quick sanity check."""
    cfg = ModelConfig(vocab_size=1100, d_model=256, n_heads=8, n_layers=6, d_ff=1024, max_seq_len=512)
    model = LogikoLM(cfg)
    n_params = model.num_parameters()
    print(f"Model: {n_params:,} parameters ({n_params/1e6:.2f}M)")
    print(f"Config: {cfg}")
    # 前向测试
    B, T = 2, 64
    idx = torch.randint(4, 1100, (B, T))
    targets = idx.clone()
    logits, loss = model(idx, targets)
    print(f"Forward OK. logits shape: {logits.shape}, loss: {loss.item():.4f}")

if __name__ == "__main__":
    main()
