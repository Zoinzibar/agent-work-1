#!/usr/bin/env python3
"""KV-cache arithmetic used by docs/workflow.md §4.1.

Formula (full attention, separate K and V):
  bytes/token = 2 * layers * kv_heads * head_dim * bytes_per_element

Presets use geometries verified from config.json on 2026-09-27, or are
labelled UNVERIFIED (see docs/sources.md, "Unverified leads"). This script
does not allocate memory and does not include the vision projector, CUDA
context, or compute buffers.
The managed runtime's fit badge is the check that counts.

Usage:
  python scripts/kv_cache.py --preset qwen3.8-27b
  python scripts/kv_cache.py --preset gemma4-26b-a4b
  python scripts/kv_cache.py --layers 80 --kv-heads 8 --head-dim 128 --ctx 65536
  python scripts/kv_cache.py --config path/to/config.json --ctx 65536
  python scripts/kv_cache.py --preset qwen3.8-27b --weights-gb 16.5   # adds a fit line
"""
import argparse
import json
import sys
from collections import Counter

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
            # Gated DeltaNet convolves Q, K and V together:
            # 2 * (16 key heads * 128) + 48 value heads * 128 = 10240 channels.
            "conv_channels": 2 * 16 * 128 + 48 * 128,
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
        "source": "UNVERIFIED geometry (last checked 2026-09-26)",
        "full_layers": 80,
        "kv_heads": 8,
        "head_dim": 128,
        "note": "Standard Llama 3.3 70B geometry. Confirm against config.json before quoting.",
    },
    "hermes-4.3-36b": {
        "source": "UNVERIFIED: Seed-OSS-36B config geometry (last checked 2026-09-26)",
        "full_layers": 64,
        "kv_heads": 8,
        "head_dim": 128,
        "note": "Confirm against the installed model's config before quoting.",
    },
    "qwen3-coder-30b-a3b": {
        "source": "UNVERIFIED geometry (last checked 2026-09-26); repo existence verified",
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


def linear_state_bytes(state):
    """(recurrent, conv) bytes for a Gated DeltaNet style fixed state. Pure function."""
    recurrent = (
        state["layers"]
        * state["v_heads"]
        * state["k_dim"]
        * state["v_dim"]
        * state["dtype_bytes"]
    )
    conv = state["layers"] * state["conv_kernel"] * state["conv_channels"] * state["dtype_bytes"]
    return recurrent, conv


def linear_state_from_config(text, n_linear):
    """Build a linear_state dict from a Qwen3.5-style text_config, or None if fields are absent."""
    keys = ("linear_num_key_heads", "linear_num_value_heads", "linear_key_head_dim", "linear_value_head_dim")
    if n_linear <= 0 or any(text.get(k) is None for k in keys):
        return None
    k_heads, v_heads = text["linear_num_key_heads"], text["linear_num_value_heads"]
    k_dim, v_dim = text["linear_key_head_dim"], text["linear_value_head_dim"]
    dtype_bytes = 4 if str(text.get("mamba_ssm_dtype", "float32")) == "float32" else 2
    return {
        "layers": n_linear,
        "v_heads": v_heads,
        "k_dim": k_dim,
        "v_dim": v_dim,
        "dtype_bytes": dtype_bytes,
        "conv_kernel": text.get("linear_conv_kernel_dim", 4),
        "conv_channels": 2 * k_heads * k_dim + v_heads * v_dim,
    }


def print_fit(weights_gb, cache_bytes, vram_gib):
    """Weights (decimal GB, as Hugging Face lists files) + cache, in GiB, against a VRAM budget."""
    weights_gib = weights_gb * 1000 ** 3 / 1024 ** 3
    cache_gib = cache_bytes / 1024 ** 3
    total = weights_gib + cache_gib
    print(f"\nFit estimate (weights + cache/state only):")
    print(f"  weights {weights_gb} GB decimal = {weights_gib:.2f} GiB")
    print(f"  cache/state = {cache_gib:.2f} GiB")
    print(f"  sum = {total:.2f} GiB of {vram_gib} GiB -> headroom {vram_gib - total:.2f} GiB before buffers")
    if total > vram_gib:
        print("  DOES NOT FIT before projector, CUDA context and compute buffers are even counted.")
    return total


def print_qwen_linear(state):
    recurrent, conv = linear_state_bytes(state)
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
    low, high = slide_total * 0.5 + g_total, slide_total + g_total * 2
    print(f"\nRange at this context, before weights and buffers: {fmt(low)} to {fmt(high)}")
    print("Do not add a blog GGUF size to this range and call the sum measured.")
    return low, high


def main(argv=None):
    p = argparse.ArgumentParser(description="KV cache calculator for docs/workflow.md §4.1")
    p.add_argument("--preset", choices=sorted(PRESETS), help="named geometry from the workflow")
    p.add_argument("--layers", type=int)
    p.add_argument("--kv-heads", type=int)
    p.add_argument("--head-dim", type=int)
    p.add_argument("--ctx", type=int, default=65536)
    p.add_argument("--dtype", default="fp16", choices=list(DTYPE_BYTES))
    p.add_argument("--config", help="path to config.json (reads text_config if present)")
    p.add_argument(
        "--full-attn-only",
        type=int,
        help="override the number of full-attention layers counted in the growing cache",
    )
    p.add_argument(
        "--weights-gb",
        type=float,
        help="GGUF file size in decimal GB as listed on Hugging Face; prints a weights+cache fit line",
    )
    p.add_argument("--vram-gib", type=float, default=24.0, help="VRAM budget for the fit line (default 24)")
    args = p.parse_args(argv)
    dtype_bytes = DTYPE_BYTES[args.dtype]

    def finish(cache_bytes):
        if args.weights_gb is not None:
            print_fit(args.weights_gb, cache_bytes, args.vram_gib)
        return 0

    if args.preset:
        preset = PRESETS[args.preset]
        print(f"Preset: {args.preset}")
        if "sliding" in preset:
            _, high = print_gemma(preset, args.ctx, args.dtype, dtype_bytes)
            if args.weights_gb is not None:
                print("(fit line uses the HIGH end of the range)")
            return finish(high)
        print(f"Source: {preset['source']}")
        print(preset["note"])
        print()
        total = print_standard(
            preset["full_layers"], preset["kv_heads"], preset["head_dim"],
            args.ctx, args.dtype, dtype_bytes,
        )
        if "linear_state" in preset:
            total += print_qwen_linear(preset["linear_state"])
        print("\nNot included: vision projector, CUDA context, compute buffers.")
        print("q8_0 / q4_0 figures ignore block scales, so they are slightly low.")
        return finish(total)

    if args.config:
        with open(args.config) as f:
            cfg = json.load(f)
        text = cfg.get("text_config", cfg)
        layers = text.get("num_hidden_layers")
        kv_heads = text.get("num_key_value_heads") or text.get("num_attention_heads")
        head_dim = text.get("head_dim")
        if not head_dim and text.get("hidden_size") and text.get("num_attention_heads"):
            head_dim = text["hidden_size"] // text["num_attention_heads"]
        if None in (layers, kv_heads, head_dim):
            p.error(
                f"config is missing geometry (num_hidden_layers={layers}, "
                f"num_key_value_heads={kv_heads}, head_dim={head_dim}); pass --layers/--kv-heads/--head-dim"
            )
        print(f"Loaded config: layers={layers}, kv_heads={kv_heads}, head_dim={head_dim}")
        counts = Counter(text.get("layer_types") or [])
        linear_state = None
        if counts:
            print(f"layer_types: {dict(counts)}")
            if counts.get("sliding_attention"):
                print("Sliding-window layers present. They are left out of the growing cache, and this")
                print("path cannot model a separate global geometry; prefer --preset gemma4-26b-a4b.")
            if not args.full_attn_only:
                # Count only full_attention layers, including zero: linear/sliding layers
                # must never land in the growing cache (they are counted separately, if at all).
                layers = counts.get("full_attention", 0)
                print(f"Growing cache counts only the {layers} full_attention layers.")
            linear_state = linear_state_from_config(text, counts.get("linear_attention", 0))
        if args.full_attn_only:
            print(f"Using --full-attn-only={args.full_attn_only}.")
            layers = args.full_attn_only
        print()
        if layers:
            total = print_standard(layers, kv_heads, head_dim, args.ctx, args.dtype, dtype_bytes)
        else:
            total = 0
            print("  No full_attention layers: the growing KV cache is 0 bytes at any context.")
        if linear_state:
            total += print_qwen_linear(linear_state)
        return finish(total)

    if None in (args.layers, args.kv_heads, args.head_dim):
        p.error("Need --preset, or --layers --kv-heads --head-dim, or --config")
    total = print_standard(args.layers, args.kv_heads, args.head_dim, args.ctx, args.dtype, dtype_bytes)
    return finish(total)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
