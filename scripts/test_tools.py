#!/usr/bin/env python3
"""Send one trivial tool call to a planner route. Dry-run unless --send.

updated-workflow.md §5: a marketing page that says "tools" is not enough.
This script asks the route to call `add`, with arguments 2 and 3. It does not
browse, execute code, or read secrets. The API key is read from the
environment and never printed.

Usage:
  python scripts/test_tools.py --provider anthropic --model claude-opus-5-5
  python scripts/test_tools.py --provider openai --model gpt-6-sol --send
  python scripts/test_tools.py --provider openai --base-url https://openrouter.ai/api/v1 \\
      --model anthropic/claude-opus-5-5 --send

Keys: ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY.

Exit status: 0 = add(a=2, b=3) came back as a structured tool call (or dry run),
1 = the route answered but did not make that call, 2 = the probe did not
complete (missing key, auth/quota/5xx, transport error).
OpenRouter and Nous Portal are --provider openai with --base-url set.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

TOOL = {
    "name": "add",
    "description": "Add two integers. Test probe only.",
    "parameters": {
        "type": "object",
        "properties": {
            "a": {"type": "integer"},
            "b": {"type": "integer"},
        },
        "required": ["a", "b"],
    },
}

PROMPT = "Call the add tool with a=2 and b=3. Do not answer in prose first."


def anthropic_request(model, base_url):
    url = base_url.rstrip("/") + "/v1/messages"
    body = {
        "model": model,
        "max_tokens": 256,
        "tools": [{
            "name": TOOL["name"],
            "description": TOOL["description"],
            "input_schema": TOOL["parameters"],
        }],
        "messages": [{"role": "user", "content": PROMPT}],
    }
    return url, body, "ANTHROPIC_API_KEY", "x-api-key"


def openai_request(model, base_url):
    url = base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "tools": [{
            "type": "function",
            "function": {
                "name": TOOL["name"],
                "description": TOOL["description"],
                "parameters": TOOL["parameters"],
            },
        }],
        "tool_choice": "auto",
    }
    return url, body, "OPENAI_API_KEY", "Authorization"


def gemini_request(model, base_url):
    # Key goes in a header, not the URL, so it cannot land in a log via the path.
    url = base_url.rstrip("/") + f"/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": PROMPT}]}],
        "tools": [{"functionDeclarations": [{
            "name": TOOL["name"],
            "description": TOOL["description"],
            "parameters": TOOL["parameters"],
        }]}],
    }
    return url, body, "GEMINI_API_KEY", "x-goog-api-key"


def _args_ok(args):
    """True if the tool arguments are a=2, b=3 (dict or JSON string)."""
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            return False
    if not isinstance(args, dict):
        return False
    try:
        return int(args.get("a")) == 2 and int(args.get("b")) == 3
    except (TypeError, ValueError):
        return False


def find_tool_call(provider, parsed):
    """Return (called, args_ok) for an `add` call in a parsed response body.

    Walks the provider's documented response shape instead of substring-matching
    the JSON dump (the old check matched any body containing "add" and "tool_use",
    e.g. prose that mentions the tool). Pure function so it can be unit-tested.
    """
    calls = []
    if not isinstance(parsed, dict):
        return False, False
    if provider == "anthropic":
        for block in parsed.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                calls.append((block.get("name"), block.get("input")))
    elif provider == "openai":
        for choice in parsed.get("choices") or []:
            msg = (choice or {}).get("message") or {}
            for tc in msg.get("tool_calls") or []:
                fn = (tc or {}).get("function") or {}
                calls.append((fn.get("name"), fn.get("arguments")))
    elif provider == "gemini":
        for cand in parsed.get("candidates") or []:
            for part in ((cand or {}).get("content") or {}).get("parts") or []:
                fc = (part or {}).get("functionCall")
                if fc:
                    calls.append((fc.get("name"), fc.get("args")))
    adds = [args for name, args in calls if name == TOOL["name"]]
    return bool(adds), any(_args_ok(a) for a in adds)


def main(argv=None):
    p = argparse.ArgumentParser(description="One tool-call probe. Dry-run by default.")
    p.add_argument("--provider", required=True, choices=["anthropic", "openai", "gemini"])
    p.add_argument("--model", required=True)
    p.add_argument("--base-url", default=None, help="override the vendor base URL")
    p.add_argument("--send", action="store_true", help="actually send; requires the env key")
    p.add_argument("--timeout", type=int, default=60)
    args = p.parse_args(argv)

    defaults = {
        "anthropic": "https://api.anthropic.com",
        "openai": "https://api.openai.com/v1",
        "gemini": "https://generativelanguage.googleapis.com",
    }
    base = args.base_url or defaults[args.provider]
    builders = {
        "anthropic": anthropic_request,
        "openai": openai_request,
        "gemini": gemini_request,
    }
    url, body, env_name, header = builders[args.provider](args.model, base)

    print(f"POST {url}")
    print(f"auth: {env_name} via {header} (value not printed)")
    print(json.dumps(body, indent=2))

    if not args.send:
        print("\nDry run. Re-invoke with --send to perform the request.")
        return 0

    key = os.environ.get(env_name)
    if not key:
        print(f"\n--send set but {env_name} is empty. Nothing sent.", file=sys.stderr)
        return 2

    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "agent-work-1-tool-probe/1.0"}
    if header == "Authorization":
        headers["Authorization"] = f"Bearer {key}"
    elif header == "x-api-key":
        headers["x-api-key"] = key
        headers["anthropic-version"] = "2023-06-01"
    else:
        headers[header] = key

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            raw = resp.read().decode()
            print(f"\nHTTP {resp.status}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        print(f"\nHTTP {e.code}")
        print(raw[:4000])
        if e.code in (401, 403, 429) or e.code >= 500:
            print("\nAuth, quota or server error. The probe did not complete; this says nothing about tools.")
            return 2
        if e.code in (400, 404, 422) and "tool" in raw.lower():
            print("\nRoute rejected tools. Do not use this id as the planner until that changes.")
        return 1
    except Exception as e:
        print(f"\nTransport error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        print(raw[:4000])
        print("\nNon-JSON body. Cannot tell whether a tool call was returned.")
        return 1

    called, args_ok = find_tool_call(args.provider, parsed)
    print(json.dumps(parsed, indent=2)[:4000])
    if called and args_ok:
        print("\nadd(a=2, b=3) tool call present. This route accepts tools for this probe.")
        return 0
    if called:
        print("\nadd() was called, but not with a=2, b=3. Tool calling works; argument fidelity does not.")
        return 1
    print("\nHTTP success, but no add() tool call found in the body.")
    print("The route may accept the schema and still have declined to call it. Inspect the body.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
