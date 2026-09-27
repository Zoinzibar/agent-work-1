#!/usr/bin/env python3
"""
Check if recommended local models actually exist on Hugging Face.
This addresses second-order hallucination risk: Qwen3-Coder 32B did not exist,
Qwen3.8-27B may not either.

Usage:
  python scripts/check_model_existence.py
  python scripts/check_model_existence.py --models Qwen/Qwen3-30B-A3B,google/gemma-3-27b-it

Requires: requests (pip install requests) or uses urllib fallback.
"""
import sys
import json
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request
    import urllib.error

# Models claimed in updated-workflow.md §4.2 + analysis §5
MODELS_TO_CHECK = [
    # Claimed as top picks
    ("Qwen/Qwen3.8-27B", "Qwen3.8-27B ⭐ default pick - claimed 2026-08-14, 262K, Apache 2.0"),
    ("google/gemma-4-26b-a4b-it", "Gemma 4 26B-A4B throughput pick - claimed Apr 2026"),
    ("Qwen/Qwen3-Coder-30B-A3B-Instruct", "Qwen3-Coder-30B-A3B - claimed real, 50.3% SWE-bench"),
    ("openai/gpt-oss-20b", "gpt-oss-20B headroom pick - Aug 2025"),
    ("Qwen/Qwen3-27B", "Qwen3 27B (Qwen3.6-27B superseded)"),
    ("NousResearch/Hermes-4.3-36B", "Hermes 4.3 36B - Dec 2025, Psyche"),
    ("NousResearch/Hermes-4-405B", "Hermes 4 405B planner - Aug 2025"),
    # Known false from initial brief
    ("Qwen/Qwen3-Coder-32B-Instruct", "Qwen3-Coder 32B Instruct - SHOULD NOT EXIST (M9 ❌)"),
    # Reference
    ("ByteDance-Seed/Seed-OSS-36B-Base", "Seed-OSS-36B-Base for KV geometry"),
    ("meta-llama/Llama-3.3-70B-Instruct", "Llama 3.3 70B - for KV calc"),
]

def check_model_hf(model_id):
    url = f"https://huggingface.co/api/models/{model_id}"
    if HAS_REQUESTS:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                return True, data.get("sha"), data.get("lastModified")
            else:
                return False, r.status_code, None
        except Exception as e:
            return False, str(e), None
    else:
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                return True, data.get("sha"), data.get("lastModified")
        except urllib.error.HTTPError as e:
            return False, e.code, None
        except Exception as e:
            return False, str(e), None

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--models", help="comma-separated HF model ids to check")
    args = p.parse_args()

    models = MODELS_TO_CHECK
    if args.models:
        models = [(m.strip(), "custom") for m in args.models.split(",")]

    print(f"Checking {len(models)} models on Hugging Face API...\n")
    print(f"{'Model ID':<45} {'Exists':<8} {'Note'}")
    print("-"*120)
    missing = []
    exists = []
    for model_id, note in models:
        ok, extra, last_mod = check_model_hf(model_id)
        status = "✅" if ok else "❌"
        print(f"{model_id:<45} {status:<8} {note} ({extra})")
        if ok:
            exists.append(model_id)
        else:
            missing.append((model_id, note))

    print("\n--- Summary ---")
    print(f"Exists: {len(exists)}/{len(models)}")
    print(f"Missing: {len(missing)}/{len(models)}")
    if missing:
        print("\nMissing models (potential hallucination):")
        for mid, note in missing:
            print(f"  - {mid}: {note}")
        print("\n⚠️  If Qwen3.8-27B or Gemma 4 26B-A4B are missing, updated-workflow.md's top picks are unverified.")
        print("    Treat them as CANDIDATE, not CONFIRMED, until primary HF repo appears.")

    # Also check Hermes Agent framework existence
    print("\n--- Framework existence checks (manual) ---")
    print("These require manual curl -I, not HF API:")
    print("  - https://hermes-agent.nousresearch.com/docs/llms.txt")
    print("  - https://github.com/NousResearch/hermes-agent")
    print("  - OpenRouter: https://openrouter.ai/nousresearch/hermes-4-405b")
    print("\nIf hermes-agent.nousresearch.com returns 404/DNS fail, F1-F6 scorecard is circular.")

if __name__ == "__main__":
    main()
