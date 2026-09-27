#!/usr/bin/env python3
"""Check Hugging Face for the model IDs named in updated-workflow.md.

Three rules, learned the hard way:

1. A transport error is not a 404. The first version printed TLS failures as
   "model missing / potential hallucination". Only a Hub not-found answer
   counts as missing.
2. Anonymous requests for a repo that does not exist get **HTTP 401** with the
   body ``{"error":"Invalid username or password."}`` — the Hub does not reveal
   whether the repo is missing or private. With a token (``HF_TOKEN``) the same
   lookup returns a plain 404. Both are classified as ``missing`` here; the
   anonymous case is labelled "missing or private".
3. Existence is not endorsement. This script pins the SHA that was read on
   2026-09-27 so a moved revision is loud, but it says nothing about quality.

Exit status: 0 if every lookup completed and matched expectations,
1 if a lookup completed but did not match (SHA moved, known-false id exists,
recommended id missing), 2 if any lookup did not complete.

Usage:
  python scripts/check_model_existence.py
  python scripts/check_model_existence.py --models Qwen/Qwen3.8-27B,google/gemma-4-26B-A4B-it
  HF_TOKEN=hf_... python scripts/check_model_existence.py
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

# (id, expect_exists, note)
# expect_exists False means "missing" is the desired result (the known-false brief pick).
MODELS = [
    ("Qwen/Qwen3.8-27B", True, "default local weight (judgment, not a ranking)"),
    ("google/gemma-4-26B-A4B-it", True, "throughput candidate"),
    ("openai/gpt-oss-20b", True, "headroom candidate"),
    ("Qwen/Qwen3-Coder-30B-A3B-Instruct", True, "carried fallback; existence re-read 2026-09-27, geometry still carried"),
    ("NousResearch/Hermes-4-405B", True, "weights exist; still not the planner"),
    ("Qwen/Qwen3-Coder-32B-Instruct", False, "brief headline pick; 'missing' is the expected result (analysis M9)"),
]

# Revision SHAs as read from https://huggingface.co/api/models/<id> on 2026-09-27.
# A different SHA is not an error in itself; it means the card/config may have
# changed since the workflow's numbers were derived. Re-read §4 before downloading.
PINNED_SHA = {
    "Qwen/Qwen3.8-27B": "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0",
    "google/gemma-4-26B-A4B-it": "4d7ae4984b7db7de8f8457170b3f1a419ee76d52",
    "openai/gpt-oss-20b": "6cee5e81ee83917806bbde320786a8fb61efebee",
    "Qwen/Qwen3-Coder-30B-A3B-Instruct": "b2cff646eb4bb1d68355c01b18ae02e7cf42d120",
    "NousResearch/Hermes-4-405B": "88e3dce03c4a5535e2f4a2bcc08e939a2b302f82",
}
PIN_DATE = "2026-09-27"

UA = "agent-work-1-check/1.1 (existence check; not a scraper)"
HUB_ANON_NOT_FOUND = "invalid username or password"


def classify_http_error(code, body):
    """Map an HTTPError to a status. Pure function so it can be unit-tested."""
    if code == 404:
        return {"status": "missing", "http": 404, "detail": "HTTP 404"}
    if code == 401 and HUB_ANON_NOT_FOUND in (body or "").lower():
        return {
            "status": "missing",
            "http": 401,
            "detail": "HTTP 401 anonymous not-found (repo missing or private; set HF_TOKEN to distinguish)",
        }
    return {"status": "http_error", "http": code, "detail": f"HTTP {code} {body[:120] if body else ''}".strip()}


def lookup(model_id, token=None, timeout=20):
    url = f"https://huggingface.co/api/models/{model_id}"
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            return {
                "status": "exists",
                "http": resp.status,
                "sha": data.get("sha"),
                "last_modified": data.get("lastModified"),
                "private": data.get("private"),
                "gated": data.get("gated"),
            }
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode(errors="replace")
        except Exception:  # pragma: no cover - body read is best effort
            body = ""
        return classify_http_error(e.code, body)
    except Exception as e:
        return {"status": "transport_error", "http": None, "detail": f"{type(e).__name__}: {e}"}


def evaluate(model_id, expect_exists, result):
    """Return (label_lines, is_incomplete, is_unexpected) for one lookup result."""
    lines = []
    status = result["status"]
    if status == "exists":
        sha = result.get("sha") or ""
        pin = PINNED_SHA.get(model_id)
        unexpected = False
        pin_note = ""
        if pin and sha and sha != pin:
            pin_note = f"  SHA MOVED (pinned {pin} on {PIN_DATE})"
            unexpected = True
        elif pin and sha == pin:
            pin_note = f"  SHA matches {PIN_DATE} pin"
        lines.append(f"EXISTS   {model_id}")
        gated = result.get("gated")
        gated_note = f" gated={gated}" if gated else ""
        lines.append(f"         sha={sha} lastModified={result.get('last_modified')}{gated_note}{pin_note}")
        if not expect_exists:
            lines.append("         UNEXPECTED: this id was supposed to be missing")
            unexpected = True
        return lines, False, unexpected
    if status == "missing":
        lines.append(f"MISSING  {model_id}  {result.get('detail')}")
        if expect_exists:
            lines.append("         unexpected for a recommended id — do not download from memory")
            return lines, False, True
        lines.append("         expected (known-false id)")
        return lines, False, False
    lines.append(f"INCOMPLETE  {model_id}  {status} {result.get('detail')}")
    lines.append("         not evidence of absence. Retry, or open the Hub URL in a browser.")
    return lines, True, False


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--models", help="comma-separated HF ids; all are expected to exist")
    p.add_argument("--timeout", type=int, default=20, help="per-request timeout in seconds")
    args = p.parse_args(argv)

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")

    if args.models:
        rows = [(m.strip(), True, "custom") for m in args.models.split(",") if m.strip()]
    else:
        rows = MODELS

    print(f"Checking {len(rows)} Hugging Face model ids ({'with' if token else 'without'} HF_TOKEN)\n")
    incomplete = []
    unexpected = []
    for model_id, expect_exists, note in rows:
        result = lookup(model_id, token=token, timeout=args.timeout)
        lines, is_incomplete, is_unexpected = evaluate(model_id, expect_exists, result)
        for line in lines:
            print(line)
        print(f"         {note}")
        if is_incomplete:
            incomplete.append(model_id)
        if is_unexpected:
            unexpected.append(model_id)

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
