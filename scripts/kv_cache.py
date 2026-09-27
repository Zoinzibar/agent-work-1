#!/usr/bin/env python3
"""KV-cache arithmetic used by updated-workflow.md §4.1.

Formula (full attention, separate K and V):
  bytes/token = 2 * layers * kv_heads * head_dim * bytes_per_element

Presets match geometries fetched 2026-09-27, or geometries carried from the
2026-09-26 analysis and labeled as such. This script does not allocate memory
and does not include the vision projector, CUDA context, or compute buffers.
The managed runtime's fit badge is the check that counts.

Usage:
  python scripts/kv_cache.py --preset qwen3.8-27b
  python scripts/kv_cache.py --preset gemma4-26b-a4b
  python scripts/kv_cache.py --layers 80 --kv-heads 8 --head-dim 128 --ctx 65536
  python scripts/kv_cache.py --config path/to/config.json --ctx 65536
"""
import argparse
import json
import sys

DTYPE_BYTES = {
    "fp16": 2.0,
    "bf16": 2.0,
    "fp32": 4.0,
    "q8_0": 1.0,   # element size only; ignores block scales
    "q4_0": 0.5,
}

# Geometries. "source" is what this revision actually fetched.
PRESETS = {
    "qwen3.8-27b": {
        "source": "fetched config.json 2026-09-27, Qwen/Qwen3.8-27B",
        "full_layers": 16,
        "kv_heads": 4,
        "head_dim": 256,
        "note": (
            "Full-attention term only. 48 linear_attention layers are not in "
            "this product. A fixed recurrent-state estimate is printed separately."
        ),
        "linear_state": {
            "layers": 48,
            "v_heads": 48,
            "k_dim": 128,
            "v_dim": 128,
            "dtype_bytes": 4,  # mamba_ssm_dtype = float32
            "conv_kernel": 4,
            "conv_channels": 16 * 128 + 48 * 128,
        },
    },
    "gemma4-26b-a4b": {
        "source": "fetched config.json 2026-09-27, google/gemma-4-26B-A4B-it",
        "note": (
            "Two-term hybrid. Sliding cache is window-capped. Global term assumes "
            "unified K=V (1x, not 2x) and global_head_dim 512, which is what the "
            "model card describes. The doubled global term is printed as the "
            "upper reading if that assumption is wrong."
        ),
        "sliding": {
            "layers": 25,
            "kv_heads": 8,
            "head_dim": 256,
            "window": 1024,
            "k_and_v": 2,
        },
        "global": {
            "layers": 5,
            "kv_heads": 2,
            "head_dim": 512,
            "k_and_v_unified": 1,
        },
    },
    "llama-3.3-70b": {
        "source": "CARRIED from analysis, not re-fetched 2026-09-27",
        "full_layers": 80,
        "kv_heads": 8,
        "head_dim": 128,
        "note": "Standard Llama 3.3 70B geometry. Confirm against config.json before quoting.",
    },
    "hermes-4.3-36b": {
        "source": "CARRIED from Seed-OSS-36B config cited in analysis §8, not re-fetched",
        "full_layers": 64,
        "kv_heads": 8,
        "head_dim": 128,
        "note": "Confirm against the installed model's config before quoting.",
    },
    "qwen3-coder-30b-a3b": {
        "source": "CARRIED from analysis, not re-fetched 2026-09-27",
        "full_layers": 48,
        "kv_heads": 4,
        "head_dim": 128,
        "note": "Confirm against config.json before quoting.",
    },
}


def fmt(n_bytes):
    gib = n_bytes / (1024 ** 3)
    gb = n_bytes / (1000 ** 3)
    return f"{n_bytes:.0f} bytes = {gib:.4f} GiB = {gb:.4f} GB"


def kv_bytes_per_token(layers, kv_heads, head_dim, dtype_bytes, k_and_v=2):
    return k_and_v * layers * kv_heads * head_dim * dtype_bytes


def print_standard(layers, kv_heads, head_dim, ctx, dtype, dtype_bytes, k_and_v=2):
    bpt = kv_bytes_per_token(layers, kv_heads, head_dim, dtype_bytes, k_and_v)
    total = bpt * ctx
    print(f"  bytes/token ({dtype}, K+V factor {k_and_v}): {bpt:.0f} = {bpt / 1024:.1f} KiB")
    print(f"  at {ctx} tokens: {fmt(total)}")
    print(
        f"  breakdown: {k_and_v} * {layers} layers * {kv_heads} kv_heads * "
        f"{head_dim} head_dim * {dtype_bytes} B"
    )
    return total


def print_qwen_linear(state):
    recurrent = (
        state["layers"]
        * state["v_heads"]
        * state["k_dim"]
        * state["v_dim"]
        * state["dtype_bytes"]
    )
    conv = state["layers"] * state["conv_kernel"] * state["conv_channels"] * state["dtype_bytes"]
    print("\nLinear-attention state (estimate, NOT measured, does not grow with context):")
    print(
        f"  assumed recurrent: {state['layers']} layers * {state['v_heads']} v_heads * "
        f"{state['k_dim']} * {state['v_dim']} * {state['dtype_bytes']} B = {fmt(recurrent)}"
    )
    print(f"  assumed conv state: {fmt(conv)}")
    print(f"  combined: {fmt(recurrent + conv)}")
    print("  If the runtime's state layout differs, this term changes. The full-attention KV term does not.")
    return recurrent + conv


def print_gemma(preset, ctx, dtype, dtype_bytes):
    sliding = preset["sliding"]
    glob = preset["global"]
    print(f"Source: {preset['source']}")
    print(preset["note"])
    print("\nSliding layers (window-capped, separate K+V assumed):")
    bpt = kv_bytes_per_token(
        sliding["layers"], sliding["kv_heads"], sliding["head_dim"], dtype_bytes, sliding["k_and_v"]
    )
    # bpt already includes every sliding layer. The cache holds `window` tokens, not `ctx`.
    cached = min(ctx, sliding["window"])
    slide_total = bpt * cached
    print(
        f"  {sliding['layers']} layers * {sliding['k_and_v']} * {sliding['kv_heads']} kv * "
        f"{sliding['head_dim']} * {dtype_bytes} B * {cached} cached tokens"
    )
    print(f"  {fmt(slide_total)}")
    print("  If unified K=V also applies to sliding layers, about half of this.")

    print("\nGlobal layers, unified K=V (factor 1), global_head_dim:")
    g_bpt = kv_bytes_per_token(
        glob["layers"], glob["kv_heads"], glob["head_dim"], dtype_bytes, glob["k_and_v_unified"]
    )
    g_total = g_bpt * ctx
    print(f"  bytes/token: {g_bpt:.0f} = {g_bpt / 1024:.1f} KiB")
    print(f"  at {ctx} tokens: {fmt(g_total)}")
    print(f"  if NOT unified (factor 2): {fmt(g_total * 2)}")
    print(f"\nRange at this context, before weights and buffers: {fmt(slide_total * 0.5 + g_total)} to {fmt(slide_total + g_total * 2)}")
    print("Do not add a blog GGUF size to this range and call the sum measured.")


def main(argv=None):
    p = argparse.ArgumentParser(description="KV cache calculator for updated-workflow.md §4.1")
    p.add_argument("--preset", choices=sorted(PRESETS), help="named geometry from the workflow")
    p.add_argument("--layers", type=int)
    p.add_argument("--kv-heads", type=int)
    p.add_argument("--head-dim", type=int)
    p.add_argument("--ctx", type=int, default=65536)
    p.add_argument("--dtype", default="fp16", choices=list(DTYPE_BYTES))
    p.add_argument("--config", help="path to config.json (full-attention fields only)")
    p.add_argument(
        "--full-attn-only",
        type=int,
        help="if --config is a hybrid model, use this many full-attention layers",
    )
    args = p.parse_args(argv)
    dtype_bytes = DTYPE_BYTES[args.dtype]

    if args.preset:
        preset = PRESETS[args.preset]
        print(f"Preset: {args.preset}")
        if "sliding" in preset:
            print_gemma(preset, args.ctx, args.dtype, dtype_bytes)
            return
        print(f"Source: {preset['source']}")
        print(preset["note"])
        print()
        print_standard(
            preset["full_layers"], preset["kv_heads"], preset["head_dim"],
            args.ctx, args.dtype, dtype_bytes,
        )
        if "linear_state" in preset:
            print_qwen_linear(preset["linear_state"])
        print("\nNot included: vision projector, CUDA context, compute buffers.")
        print("q8_0 / q4_0 figures ignore block scales, so they are slightly low.")
        return

    if args.config:
        with open(args.config) as f:
            cfg = json.load(f)
        text = cfg.get("text_config", cfg)
        layers = text.get("num_hidden_layers")
        kv_heads = text.get("num_key_value_heads")
        head_dim = text.get("head_dim") or (
            text.get("hidden_size", 0) // text.get("num_attention_heads", 1)
        )
        print(f"Loaded config: layers={layers}, kv_heads={kv_heads}, head_dim={head_dim}")
        layer_types = text.get("layer_types") or []
        if layer_types:
            from collections import Counter
            counts = Counter(layer_types)
            print(f"layer_types: {dict(counts)}")
            print("Hybrid configs: this path uses num_hidden_layers unless --full-attn-only is set.")
            print("Prefer --preset qwen3.8-27b or --preset gemma4-26b-a4b for those models.")
        if args.full_attn_only:
            print(f"Using --full-attn-only={args.full_attn_only}. Linear/sliding layers are excluded from the growing cache.")
            layers = args.full_attn_only
        print()
        print_standard(layers, kv_heads, head_dim, args.ctx, args.dtype, dtype_bytes)
        return

    if None in (args.layers, args.kv_heads, args.head_dim):
        p.error("Need --preset, or --layers --kv-heads --head-dim, or --config")
    print_standard(args.layers, args.kv_heads, args.head_dim, args.ctx, args.dtype, dtype_bytes)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
