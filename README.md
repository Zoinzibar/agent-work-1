# agent-work-1

## Hermes Agent / RTX 4090 research — claim verification

- [`initial-agent-research.md`](initial-agent-research.md) — the initial research brief as received
  (reproduced verbatim, with a **warning banner** and `†` navigation markers; it contains known-false
  model advice).
- [`claim-verification-analysis.md`](claim-verification-analysis.md) — independent verification of every
  checkable claim against primary sources (Hermes Agent docs, Nous Research blogs and Hugging Face model
  cards, `Seed-OSS-36B-Base` config, Qwen model cards, OpenRouter/Artificial Analysis data), with a
  scorecard, corrections, KV-cache arithmetic for the 64K context floor on a 24 GB card, a sourced
  reference list, and a corrected model/hardware stack.
- [`updated-workflow.md`](updated-workflow.md) — the workflow to follow, **revision 2026-09-27**.
  It applies the corrections from the analysis and the open items from
  [`CRITICAL_REVIEW.md`](CRITICAL_REVIEW.md) (PR #4), after a primary-source pass. It is **not**
  an absolute "safe to act on" claim. Run its §12 checklist before downloading or subscribing.
  [`provenance/2026-09-27.md`](provenance/2026-09-27.md) lists what was fetched and what was not.

**Scorecard:** 33 scored claims → **17 verified as stated**, **13 verified with material qualification**,
**3 incorrect** (plus 1 advisory row, not scored).

**The three errors — two model picks and one provider conflation:**
1. "Qwen3-Coder 32B Instruct" — the brief's headline local pick — **does not exist**, and its 71.4%
   SWE-bench figure belongs to another model.
2. The Llama 3.3 70B IQ2_XXS fallback **cannot hold a 64K KV cache**: 20 GiB of cache alone, on top of
   ~21–23 GB of weights, on a 24 GB card.
3. **xAI and Parallel are different providers**, and xAI's search results are LLM-generated rather than
   index-backed.

The framework half held up in the 2026-09-26 scorecard (11 of 16 claims verified as stated), and the
hybrid local + cloud architecture still survives. The 2026-09-27 revision keeps Qwen3.8-27B as the
default local *weight* only after confirming the Hub repo and `config.json` — and it withdraws the
AA Index "52 vs 38" figure, which was not on the model card. Planner IDs are named vendor model IDs,
not "frontier-adjacent".

### Scripts

Small, dependency-free (`python3` stdlib only). The workflow's §12 checklist tells you when to run them.

| Script | What it does | Network |
| --- | --- | --- |
| `scripts/kv_cache.py --preset <name>` | Reproduces the KV-cache rows in `updated-workflow.md` §4.1 from model geometry (`--config config.json` for your own). | none |
| `scripts/check_model_existence.py` | Asks the Hugging Face API whether each recommended id still exists and whether its revision SHA moved off the 2026-09-27 pin. Exit 0 = pass, 1 = mismatch, 2 = a lookup did not complete. Reads `HF_TOKEN` if set. | Hub API |
| `scripts/test_tools.py --provider … --model …` | Builds one minimal tool-call request for a named planner id; dry-run unless `--send`. | vendor API, only with `--send` |
| `python -m unittest discover -s tests` | Offline self-test: the §4.1 numbers, the Hub status classification, and the probe's dry-run contract. | none |

> ⏳ **Re-checked 2026-09-27, not frozen.** Before downloading anything, run
> [`updated-workflow.md`](updated-workflow.md) §12. Model IDs and prices move faster than the KV formula.
