#!/usr/bin/env python3
"""Check Hugging Face for the model IDs named in updated-workflow.md.

A transport error is not a 404. The first version of this script printed TLS
failures as "model missing / potential hallucination". That is fixed: only
HTTP 404 counts as missing. Exit status is 0 if every lookup completed
(missing models included), 2 if any lookup did not complete.

Usage:
  python scripts/check_model_existence.py
  python scripts/check_model_existence.py --models Qwen/Qwen3.8-27B,google/gemma-4-26B-A4B-it
"""
import json
import sys
import urllib.error
import urllib.request

# (id, expect_exists, note)
# expect_exists False means a 404 is the desired result (the known-false brief pick).
MODELS = [
    ("Qwen/Qwen3.8-27B", True, "default local weight; pin SHA 1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0 as of 2026-09-27"),
    ("google/gemma-4-26B-A4B-it", True, "throughput candidate"),
    ("openai/gpt-oss-20b", True, "headroom candidate"),
    ("Qwen/Qwen3-Coder-30B-A3B-Instruct", True, "carried fallback; not re-fetched in the 2026-09-27 writeup"),
    ("NousResearch/Hermes-4-405B", True, "weights exist; still not the planner"),
    ("Qwen/Qwen3-Coder-32B-Instruct", False, "brief headline pick; a 404 is the expected result (analysis M9)"),
]

PINNED_SHA = {
    "Qwen/Qwen3.8-27B": "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0",
}

UA = "agent-work-1-check/1.0 (existence check; not a scraper)"


def lookup(model_id):
    url = f"https://huggingface.co/api/models/{model_id}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
            return {
                "status": "exists",
                "http": resp.status,
                "sha": data.get("sha"),
                "last_modified": data.get("lastModified"),
                "private": data.get("private"),
            }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"status": "missing", "http": 404, "sha": None, "last_modified": None}
        return {"status": "http_error", "http": e.code, "detail": str(e)}
    except Exception as e:
        return {"status": "transport_error", "http": None, "detail": f"{type(e).__name__}: {e}"}


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--models", help="comma-separated HF ids; all are expected to exist")
    args = p.parse_args()

    if args.models:
        rows = [(m.strip(), True, "custom") for m in args.models.split(",") if m.strip()]
    else:
        rows = MODELS

    print(f"Checking {len(rows)} Hugging Face model ids\n")
    incomplete = []
    unexpected = []
    for model_id, expect_exists, note in rows:
        result = lookup(model_id)
        status = result["status"]
        if status == "exists":
            sha = result.get("sha") or ""
            pin = PINNED_SHA.get(model_id)
            pin_note = ""
            if pin and sha and sha != pin:
                pin_note = f"  SHA MOVED (pinned {pin})"
                unexpected.append(model_id)
            elif pin and sha == pin:
                pin_note = "  SHA matches 2026-09-27 pin"
            print(f"EXISTS   {model_id}")
            print(f"         sha={sha} lastModified={result.get('last_modified')}{pin_note}")
            if not expect_exists:
                print("         UNEXPECTED: this id was supposed to 404")
                unexpected.append(model_id)
        elif status == "missing":
            print(f"MISSING  {model_id}  HTTP 404")
            if expect_exists:
                print("         unexpected for a recommended id — do not download from memory")
                unexpected.append(model_id)
            else:
                print("         expected (known-false id)")
        else:
            print(f"INCOMPLETE  {model_id}  {status} {result.get('detail')}")
            print("         not evidence of absence. Retry, or open the Hub URL in a browser.")
            incomplete.append(model_id)
        print(f"         {note}")

    print("\n---")
    print("Framework, not an HF model: curl -fsSL -o /dev/null -w '%{http_code}\\n' \\")
    print("  https://hermes-agent.nousresearch.com/docs/llms.txt")
    print("A non-200 there means stop. Do not treat this script's TLS errors as that signal.")

    if incomplete:
        print(f"\n{len(incomplete)} lookup(s) did not complete. Exit 2.")
        return 2
    if unexpected:
        print(f"\n{len(unexpected)} id(s) did not match the expectation. Exit 1.")
        return 1
    print("\nAll lookups completed and matched expectations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
