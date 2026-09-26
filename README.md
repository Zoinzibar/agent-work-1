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

**Scorecard:** 33 scored claims → **17 verified as stated**, **13 verified with material qualification**,
**3 incorrect** (plus 1 advisory row, not scored).

**The errors are all in model selection:**
1. "Qwen3-Coder 32B Instruct" — the brief's headline local pick — **does not exist**, and its 71.4%
   SWE-bench figure belongs to another model.
2. The Llama 3.3 70B IQ2_XXS fallback **cannot hold a 64K KV cache**: 20 GiB of cache alone, on top of
   ~21–23 GB of weights, on a 24 GB card.
3. **xAI and Parallel are different providers**, and xAI's search results are LLM-generated rather than
   index-backed.

The framework half holds up (11 of 16 claims verified as stated), the hybrid local + cloud architecture
survives, and the local model picks are corrected in §5 — now headlined by **Qwen3.8-27B**, which
superseded the originally recommended Qwen3.6-27B six weeks before this verification ran.

> ⏳ **Model claims verified 2026-09-26.** The local-model tier changed twice during authoring and review.
> Re-check §5 and §6 before downloading anything; the framework and KV-cache sections are far more durable
> than the model picks.
