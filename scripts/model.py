#!/usr/bin/env python3
"""
Logiko Language Model v2 (Qwen3-style)
========================================
Architecture upgrades over v1:
  - Grouped Query Attention (GQA): n_kv_heads < n_heads, reduces KV cache
  - QK-Norm: RMSNorm applied to Q and K before attention, stabilizes training
  - SwiGLU MLP (kept from v1)
  - RoPE (kept from v1)
  - RMSNorm pre-norm (kept from v1)
  - No bias anywhere (kept from v1)
  - Tie embeddings (kept from v1 for small models)

References:
  - Qwen3 Technical Report (2025)
  - LLaMA 2 / 3 architecture
  - DeepNet QK-Norm paper
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
    vocab_size: int = 1500
    d_model: int = 256          # embedding / hidden dim
    n_heads: int = 8            # query attention heads
    n_kv_heads: int = 2         # key/value heads (for GQA; must divide n_heads)
    n_layers: int = 6           # transformer blocks
    d_ff: int = 1024            # SwiGLU intermediate dim
    max_seq_len: int = 512      # context window
    rope_base: float = 10000.0  # RoPE theta
    dropout: float = 0.0
    tie_embeddings: bool = True
    pad_id: int = 0
    qk_norm: bool = True        # Qwen3-style: RMSNorm on Q and K
    qk_norm_eps: float = 1e-6

    def __post_init__(self):
        assert self.d_model % self.n_heads == 0, "d_model must be divisible by n_heads"
        assert self.n_heads % self.n_kv_heads == 0, "n_heads must be divisible by n_kv_heads"
        if self.d_ff % 2 != 0:
            self.d_ff += 1


class RMSNorm(nn.Module):
    """Root Mean Square LayerNorm (no bias, no mean subtraction)."""

    def __init__(self, d: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(d))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        norm = torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True) + self.eps)
        return x * norm * self.weight


def precompute_rope(d_head: int, max_seq_len: int, base: float = 10000.0, device=None) -> Tuple[torch.Tensor, torch.Tensor]:
    """Precompute RoPE cos/sin tables of shape (max_seq_len, d_head)."""
    half = d_head // 2
    freqs = 1.0 / (base ** (torch.arange(0, half, device=device).float() / half))
    t = torch.arange(max_seq_len, device=device).float()
    angles = torch.outer(t, freqs)
    cos = torch.cat([angles.cos(), angles.cos()], dim=-1)
    sin = torch.cat([angles.sin(), angles.sin()], dim=-1)
    return cos, sin


def apply_rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
    """Apply RoPE to x of shape (B, H, T, D). cos, sin: (T, D)."""
    T = x.size(-2)
    cos = cos[:T].unsqueeze(0).unsqueeze(0)
    sin = sin[:T].unsqueeze(0).unsqueeze(0)
    x1 = x[..., : x.size(-1) // 2]
    x2 = x[..., x.size(-1) // 2 :]
    rotated = torch.cat([-x2, x1], dim=-1)
    return x * cos + rotated * sin


class GroupedQueryAttention(nn.Module):
    """GQA + RoPE + QK-Norm (Qwen3-style).
    If n_kv_heads == n_heads, this is standard MHA.
    If n_kv_heads == 1, this is MQA.
    Otherwise, this is GQA.
    """

    def __init__(self, cfg: ModelConfig):
        super().__init__()
        assert cfg.d_model % cfg.n_heads == 0
        assert cfg.n_heads % cfg.n_kv_heads == 0
        self.n_heads = cfg.n_heads
        self.n_kv_heads = cfg.n_kv_heads
        self.n_rep = cfg.n_heads // cfg.n_kv_heads  # repeat factor for KV
        self.d_head = cfg.d_model // cfg.n_heads

        # Q projection: d_model -> n_heads * d_head
        self.q_proj = nn.Linear(cfg.d_model, cfg.n_heads * self.d_head, bias=False)
        # K, V projection: d_model -> n_kv_heads * d_head (smaller)
        self.k_proj = nn.Linear(cfg.d_model, cfg.n_kv_heads * self.d_head, bias=False)
        self.v_proj = nn.Linear(cfg.d_model, cfg.n_kv_heads * self.d_head, bias=False)
        # Output projection
        self.o_proj = nn.Linear(cfg.d_model, cfg.d_model, bias=False)

        # QK-Norm (Qwen3-style): RMSNorm on each head's Q and K
        self.qk_norm = cfg.qk_norm
        if self.qk_norm:
            self.q_norm = RMSNorm(self.d_head, eps=cfg.qk_norm_eps)
            self.k_norm = RMSNorm(self.d_head, eps=cfg.qk_norm_eps)

        self.dropout = cfg.dropout
        # RoPE buffers
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

        q = self.q_proj(x).view(B, T, self.n_heads, self.d_head).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.n_kv_heads, self.d_head).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.n_kv_heads, self.d_head).transpose(1, 2)
        # q: (B, n_heads, T, d_head)
        # k, v: (B, n_kv_heads, T, d_head)

        # QK-Norm: apply RMSNorm to each head's Q and K
        if self.qk_norm:
            q = self.q_norm(q)
            k = self.k_norm(k)

        # RoPE
        q = apply_rope(q, self.rope_cos, self.rope_sin)
        k = apply_rope(k, self.rope_cos, self.rope_sin)

        # Repeat KV heads to match Q heads (GQA)
        if self.n_rep > 1:
            # (B, n_kv_heads, T, d_head) -> (B, n_heads, T, d_head)
            k = k.repeat_interleave(self.n_rep, dim=1)
            v = v.repeat_interleave(self.n_rep, dim=1)

        # Scaled dot-product attention (flash path if available)
        out = F.scaled_dot_product_attention(
            q, k, v,
            dropout_p=self.dropout if self.training else 0.0,
            is_causal=True,
        )
        # (B, n_heads, T, d_head) -> (B, T, C)
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.o_proj(out)


class SwiGLU(nn.Module):
    """SwiGLU MLP: out = (silu(x @ w_gate) * (x @ w_up)) @ w_down"""

    def __init__(self, d_model: int, d_ff: int, dropout: float = 0.0):
        super().__init__()
        self.w_gate = nn.Linear(d_model, d_ff, bias=False)
        self.w_up = nn.Linear(d_model, d_ff, bias=False)
        self.w_down = nn.Linear(d_ff, d_model, bias=False)
        self.dropout = dropout

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        g = F.silu(self.w_gate(x))
        u = self.w_up(x)
        return self.w_down(F.dropout(g * u, p=self.dropout, training=self.training))


class TransformerBlock(nn.Module):
    """Pre-norm transformer block: GQA + SwiGLU with residual connections."""

    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.norm1 = RMSNorm(cfg.d_model)
        self.attn = GroupedQueryAttention(cfg)
        self.norm2 = RMSNorm(cfg.d_model)
        self.mlp = SwiGLU(cfg.d_model, cfg.d_ff, dropout=cfg.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.norm1(x))
        x = x + self.mlp(self.norm2(x))
        return x


class LogikoLM(nn.Module):
    """GPT/Qwen3-style decoder-only LM."""

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
        x = self.token_embed(idx)
        for block in self.blocks:
            x = block(x)
        x = self.norm_f(x)
        logits = self.lm_head(x)
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


def build_model(
    vocab_size: int = 1500,
    d_model: int = 256,
    n_heads: int = 8,
    n_kv_heads: int = 2,
    n_layers: int = 6,
    d_ff: int = 1024,
    max_seq_len: int = 512,
    qk_norm: bool = True,
) -> LogikoLM:
    cfg = ModelConfig(
        vocab_size=vocab_size,
        d_model=d_model,
        n_heads=n_heads,
        n_kv_heads=n_kv_heads,
        n_layers=n_layers,
        d_ff=d_ff,
        max_seq_len=max_seq_len,
        qk_norm=qk_norm,
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
    cfg = ModelConfig(
        vocab_size=1500, d_model=256, n_heads=8, n_kv_heads=2,
        n_layers=6, d_ff=1024, max_seq_len=512, qk_norm=True,
    )
    model = LogikoLM(cfg)
    n_params = model.num_parameters()
    print(f"Model (Qwen3-style GQA + QK-Norm): {n_params:,} parameters ({n_params/1e6:.2f}M)")
    print(f"Config: d_model={cfg.d_model}, n_heads={cfg.n_heads}, n_kv_heads={cfg.n_kv_heads}, "
          f"n_layers={cfg.n_layers}, d_ff={cfg.d_ff}, qk_norm={cfg.qk_norm}")
    B, T = 2, 64
    idx = torch.randint(4, 1500, (B, T))
    targets = idx.clone()
    logits, loss = model(idx, targets)
    print(f"Forward OK. logits shape: {logits.shape}, loss: {loss.item():.4f}")


if __name__ == "__main__":
    main()
