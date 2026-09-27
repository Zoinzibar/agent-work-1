# Hermes Agent on Arch Linux + RTX 4090: web search and deep research

A setup guide for running [Hermes Agent](https://github.com/NousResearch/hermes-agent) with
built-in web search and a composed deep-research loop. It targets **one 24 GB RTX 4090 on Arch
Linux**, with a local model for cheap steps and a cloud planner for multi-hop reasoning.
Every load-bearing claim is labelled Verified, Derived, Unverified or Judgment and tied to a
source.

**Last verified: 2026-09-27.** Model IDs and prices move fast; run the checklist before acting.

## Read

- **[`docs/workflow.md`](docs/workflow.md)**: the guide. Start with §0 (summary) and finish with
  §10 (checklist before you download or subscribe).
- [`docs/sources.md`](docs/sources.md): Hugging Face SHA pins, sources, unverified leads, and a
  list of **known-false claims** not to repeat.
- [`AGENTS.md`](AGENTS.md): maintenance rules for anyone (human or agent) updating the repo.

## At a glance

| Layer | Pick |
| --- | --- |
| Local model | `Qwen/Qwen3.8-27B`, Unsloth `UD-Q4_K_M`: ≈19.5 GiB with a 64K fp16 cache, before buffers |
| Planner | `claude-opus-5-5` / `claude-sonnet-5` / `gpt-6-sol` / `gemini-3.8-flash`, **after** a live tool-call test |
| Web search | Keyed Firecrawl, or SearXNG plus a keyed extractor; keyless ring only as failover |
| Won't fit on one 4090 at 64K | Llama 3.3 70B, Hermes 4.3 36B; Hermes 4 405B is not a planner |

## Scripts

Python 3.9+ standard library only; no install needed.

```bash
python scripts/kv_cache.py --preset qwen3.8-27b --weights-gb 16.5   # KV cache + fit vs 24 GiB
python scripts/kv_cache.py --config path/to/config.json             # any model, hybrid-aware
python scripts/check_model_existence.py                             # Hub ids exist + SHAs match pins (network)
python scripts/test_tools.py --provider anthropic --model claude-sonnet-5          # dry run
python scripts/test_tools.py --provider anthropic --model claude-sonnet-5 --send   # live, needs API key
python -m unittest discover -s tests                                # offline self-test (also runs in CI)
```

| Script | Exit codes |
| --- | --- |
| `check_model_existence.py` | 0 all match · 1 mismatch (missing id, SHA moved, known-false id exists) · 2 lookup incomplete |
| `test_tools.py --send` | 0 structured `add(2, 3)` tool call · 1 no such call · 2 probe didn't complete (key, auth, quota, 5xx, network) |
