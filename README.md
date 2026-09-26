# agent-work-1

## Hermes Agent / RTX 4090 research — claim verification

- [`initial-agent-research.md`](initial-agent-research.md) — the initial research brief as received
  (reproduced verbatim, uncorrected).
- [`claim-verification-analysis.md`](claim-verification-analysis.md) — independent verification of every
  checkable claim against primary sources (Hermes Agent docs, Nous Research blogs and Hugging Face model
  cards, `Seed-OSS-36B-Base` config, Qwen model cards, OpenRouter/Artificial Analysis data), with a
  scorecard, corrections, KV-cache arithmetic for the 64K context floor on a 24 GB card, and a corrected
  model/hardware stack.

**Bottom line:** 33 scored claims → 22 verified, 7 partially correct, 4 incorrect. The framework claims
hold up; the model-selection claims do not (the headline local model "Qwen3-Coder 32B Instruct" does not
exist, and the IQ2 70B fallback cannot hold a 64K KV cache). The hybrid local + cloud architecture
survives, with different models.
