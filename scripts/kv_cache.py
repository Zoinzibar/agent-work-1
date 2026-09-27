#!/usr/bin/env python3
"""
KV-cache arithmetic reference implementation.
Derives KV cache size from model config.json geometry.

Formula:
  KV bytes/token = 2 (K+V) * layers * kv_heads * head_dim * bytes_per_element
  KV at context = bytes_per_token * context_len

For hybrid attention (e.g., Qwen3.8-27B: 48 DeltaNet + 16 full-attn):
  - Only full-attn layers contribute to KV cache in this model
  - DeltaNet layers assumed 0 KV (ASSUMPTION, needs verification)

Usage:
  python scripts/kv_cache.py --layers 80 --kv-heads 8 --head-dim 128 --ctx 65536 --dtype fp16
  python scripts/kv_cache.py --config path/to/config.json --ctx 65536

References:
  - Seed-OSS-36B-Base config: 64 layers, 8 KV heads, head_dim 128
  - Llama 3.3 70B: 80 layers, 8 KV, 128
  - Qwen3-Coder-30B-A3B: 48 layers, 4 KV, 128
  - Qwen3.8-27B: 16 full-attn layers, 4 KV, 256 (DeltaNet layers excluded)
"""
import argparse
import json
import sys

DTYPE_BYTES = {
    "fp16": 2,
    "bf16": 2,
    "fp32": 4,
    "q8_0": 1,
    "q4_0": 0.5,
    "q4_K_M": 0.5,  # approx, for weights only; KV is typically fp16/q8
}

def kv_bytes_per_token(layers, kv_heads, head_dim, dtype_bytes=2):
    return 2 * layers * kv_heads * head_dim * dtype_bytes

def kv_at_context(bytes_per_token, ctx):
    total_bytes = bytes_per_token * ctx
    gib = total_bytes / (1024**3)
    gb = total_bytes / (1000**3)
    return total_bytes, gib, gb

def main():
    p = argparse.ArgumentParser(description="KV cache calculator")
    p.add_argument("--layers", type=int, help="num_hidden_layers or full-attn layers")
    p.add_argument("--kv-heads", type=int, help="num_key_value_heads")
    p.add_argument("--head-dim", type=int, help="head_dim (or hidden_size // num_attention_heads)")
    p.add_argument("--ctx", type=int, default=65536, help="context length")
    p.add_argument("--dtype", default="fp16", choices=list(DTYPE_BYTES.keys()))
    p.add_argument("--config", help="path to config.json (reads num_hidden_layers, num_key_value_heads, head_dim or hidden_size)")
    p.add_argument("--full-attn-only", type=int, help="if hybrid, number of full-attn layers (e.g., 16 for Qwen3.8-27B)")
    args = p.parse_args()

    if args.config:
        with open(args.config) as f:
            cfg = json.load(f)
        layers = cfg.get("num_hidden_layers")
        kv_heads = cfg.get("num_key_value_heads")
        # head_dim may be explicit or derived
        head_dim = cfg.get("head_dim") or cfg.get("hidden_size", 0) // cfg.get("num_attention_heads", 1)
        print(f"Loaded config: layers={layers}, kv_heads={kv_heads}, head_dim={head_dim}")
        if args.full_attn_only:
            print(f"Hybrid model: using full_attn_only={args.full_attn_only} for KV (DeltaNet layers assumed 0 KV - UNVERIFIED)")
            layers = args.full_attn_only
    else:
        layers = args.layers
        kv_heads = args.kv_heads
        head_dim = args.head_dim
        if None in (layers, kv_heads, head_dim):
            p.error("Need --layers --kv-heads --head-dim or --config")

    dtype_bytes = DTYPE_BYTES[args.dtype]
    bpt = kv_bytes_per_token(layers, kv_heads, head_dim, dtype_bytes)
    total, gib, gb = kv_at_context(bpt, args.ctx)

    print(f"\nKV bytes/token ({args.dtype}): {bpt} bytes = {bpt/1024:.1f} KiB")
    print(f"KV at {args.ctx} tokens: {total} bytes = {gib:.2f} GiB = {gb:.2f} GB (decimal)")
    print(f"\nBreakdown: 2 * {layers} layers * {kv_heads} kv_heads * {head_dim} head_dim * {dtype_bytes}B = {bpt}")

    # Fit check for 24GB card
    # Example weights: Q4_K_M 27B ~17.8GB, 36B ~21.8GB
    print("\n--- Fit examples (weights + KV) on 24GB card ---")
    for w_gb, label in [(17.8, "Qwen3.8-27B Q4_K_M"), (21.8, "Hermes 4.3 36B Q4_K_M"), (23.1, "Llama 3.3 70B IQ2_XXS (claimed)")]:
        # Convert weights GB decimal to GiB for comparison? Keep simple: GB decimal
        total_gb = w_gb + gb
        # Rough GiB conversion for allocation
        total_gib = w_gb * (1000**3)/(1024**3) + gib
        status = "✅ FITS" if total_gib < 24 else "❌ OOM"
        print(f"  {label}: {w_gb} GB weights + {gb:.1f} GB KV = {total_gb:.1f} GB (~{total_gib:.1f} GiB) {status}")

    print("\nNotes:")
    print("- This script assumes all layers are full attention unless --full-attn-only is used")
    print("- DeltaNet / sliding window / hybrid attention may have different KV costs - verify per model")
    print("- GGUF file sizes are decimal GB; llama.cpp allocates GiB; this script shows both")

if __name__ == "__main__":
    main()
