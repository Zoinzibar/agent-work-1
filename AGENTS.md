# Notes for agents working in this repo

This repo is a **verified setup guide** for running Hermes Agent (Nous Research) with web search
and deep research on Arch Linux with one RTX 4090. It also contains a few stdlib-only Python
scripts that re-check the guide's volatile facts. Humans start at [`README.md`](README.md).

## Map

| Path | What it is | Edit when |
| --- | --- | --- |
| `docs/workflow.md` | The guide. The only file a user acts on. | Any recommendation, number or step changes. |
| `docs/sources.md` | Evidence ledger: Hub pins, verified URLs, unverified leads, known-false list, open contradictions. | You fetch, re-verify or refute something. |
| `scripts/kv_cache.py` | KV-cache and weights-fit arithmetic behind `workflow.md` §4.1. | Model geometry changes or a model is added. |
| `scripts/check_model_existence.py` | Checks HF ids exist and their SHAs match the pins. | Pins or the recommended ids change. |
| `scripts/test_tools.py` | One tool-call probe per planner route; dry run unless `--send`. | Vendor request/response formats change. |
| `tests/` | Offline unittest suite; `fixtures/` holds a real `config.json` subset. | With every script or §4.1 number change. |
| `.github/workflows/tests.yml` | CI: runs the tests and a script smoke test on every PR. | Rarely. |

There are no archive files. Earlier drafts, the original research brief, the claim-by-claim
grading and the PR #4 review are in git history, e.g.
`git show cbe3e37:claim-verification-analysis.md`. Don't re-add them. If something from history is still useful, fold it into `docs/`.

## Rules

1. **Primary sources only for facts.** Vendor docs, the official repo, the Hugging Face API or
   `config.json`, vendor pricing pages. Blogs and leaderboard aggregators can only be leads. See
   "Not used on purpose" in `docs/sources.md`.
2. **Label every load-bearing claim** in `workflow.md` as **Verified**, **Derived**, **Unverified**
   or **Judgment** (defined at the top of that file). If you can't re-fetch something, downgrade
   it to Unverified and put its URL in `sources.md` → Unverified leads.
3. **Date things.** Update "Last verified" in both docs when you re-verify. Model IDs and prices
   are the fastest-moving facts here.
4. **Never reintroduce anything on the known-false list** in `docs/sources.md`. If new evidence
   overturns an entry, change the entry and say why.
5. **Existence is not endorsement.** Don't call a model "best"; use role names (default,
   throughput, headroom).
6. **Keep the scripts dependency-free** (`python3` stdlib, 3.9+) and offline-testable. Network
   calls live behind explicit flags or commands, and scripts never print secrets.
7. **Run `python -m unittest discover -s tests` before committing.** If you change a number in
   `workflow.md` §4.1, a test should pin it.

## When a fact changes

| Change | Update |
| --- | --- |
| Hub SHA or recommended id | `PINNED_SHA` / `MODELS` in `scripts/check_model_existence.py`, the pin table in `docs/sources.md`, `workflow.md` §4.2 / §5 |
| Model geometry | `PRESETS` in `scripts/kv_cache.py`, the §4.1 table, the test in `tests/test_scripts.py` (and the fixture if it's Qwen3.8) |
| Planner ID or price | `workflow.md` §5 table and §7 cost table, the verified-sources row in `docs/sources.md` |
| Something turns out false | Remove it from `workflow.md` and add a row to the known-false table |

## Known environment limits

The authoring sandbox has had no direct TLS egress to `huggingface.co`, so
`check_model_existence.py` has returned exit 2 (incomplete) there. Verify through a page fetch of
the same API URL and note that in `docs/sources.md`. Don't report a transport error as "model
missing".
