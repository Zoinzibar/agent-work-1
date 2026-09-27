# Sources, pins and known-false claims

Evidence ledger for [`workflow.md`](workflow.md). **Last verified: 2026-09-27.**

When you re-verify something, update its row here and the date on it. If a pin changes, update it
in all three places listed in [`AGENTS.md`](../AGENTS.md#when-a-fact-changes).

---

## Hugging Face pins

From `GET https://huggingface.co/api/models/<id>` on 2026-09-27. These pin existence, revision SHA,
`lastModified` and the licence tag. They say nothing about quality.
`scripts/check_model_existence.py` checks against the same values.

| Id | Role | SHA | lastModified | Licence |
| --- | --- | --- | --- | --- |
| `Qwen/Qwen3.8-27B` | default local weight | `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` | 2026-08-14T15:00:01Z | apache-2.0 |
| `google/gemma-4-26B-A4B-it` | throughput candidate (public, not gated) | `4d7ae4984b7db7de8f8457170b3f1a419ee76d52` | 2026-07-20T16:42:12Z | apache-2.0 |
| `openai/gpt-oss-20b` | headroom candidate | `6cee5e81ee83917806bbde320786a8fb61efebee` | 2025-08-26T17:25:47Z | apache-2.0 |
| `Qwen/Qwen3-Coder-30B-A3B-Instruct` | tool-format fallback | `b2cff646eb4bb1d68355c01b18ae02e7cf42d120` | 2025-12-03T08:05:17Z | apache-2.0 |
| `NousResearch/Hermes-4-405B` | weights exist; **not** the planner | `88e3dce03c4a5535e2f4a2bcc08e939a2b302f82` | 2025-09-02T04:17:04Z | llama3 |
| `Qwen/Qwen3-Coder-32B-Instruct` | **known-false**; must stay missing | not found | — | — |

**How the Hub reports a missing repo.** An anonymous request for a repo that doesn't exist (or is
private) gets **HTTP 401** with body `{"error":"Invalid username or password."}`, never a 404. With
a token it gets a 404. The script treats both as "missing".

The Qwen3.8-27B `config.json` geometry the scripts use is checked in as
[`tests/fixtures/qwen3.8-27b-config.json`](../tests/fixtures/qwen3.8-27b-config.json). It is a
subset of the fields at the SHA above.

---

## Verified sources (fetched 2026-09-27)

| Used for | URL |
| --- | --- |
| Framework exists, MIT, installer, command names (HEAD `2f14d5e` at fetch time) | https://github.com/NousResearch/hermes-agent |
| Docs index (no "Deep Research" product page) | https://hermes-agent.nousresearch.com/docs/llms.txt |
| ≥64K context, 4-bit floor, RAM spill, managed runtime, amber state | https://hermes-agent.nousresearch.com/docs/user-guide/local-models |
| Backends, keyless ring, 15k head+tail extract, coalescing, xAI caveat | https://hermes-agent.nousresearch.com/docs/user-guide/features/web-search |
| `execute_code`: host child process, env scrub, whitelist, limits, modes | https://hermes-agent.nousresearch.com/docs/user-guide/features/code-execution |
| Approval modes, YOLO, container backend | https://hermes-agent.nousresearch.com/docs/user-guide/security |
| Delegation cap contradiction (guide 10; overview and config reference 3) | https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation, plus the overview and configuration pages |
| Qwen3.8-27B card, licence, chat template (`reasoning_effort` default `xhigh`), geometry | https://huggingface.co/Qwen/Qwen3.8-27B and https://huggingface.co/Qwen/Qwen3.8-27B/raw/main/config.json |
| Gemma 4 26B-A4B card, geometry, Apache 2.0 text | https://huggingface.co/google/gemma-4-26B-A4B-it and https://ai.google.dev/gemma/apache_2 |
| gpt-oss-20b: Apache 2.0, 2025-08-05, "16 GB" MXFP4 claim | https://openai.com/index/introducing-gpt-oss/ |
| Hermes 4 405B price ($1/$3, 131K) and mirrored AA panel | https://openrouter.ai/nousresearch/hermes-4-405b |
| Claude IDs and prices | https://platform.claude.com/docs/en/models/overview |
| OpenAI IDs and prices | https://developers.openai.com/api/docs/models |
| Gemini 3.8 Flash ID, function calling, intro price | https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash and https://ai.google.dev/gemini-api/docs/latest-model |
| Arch NVIDIA packages for Ada | https://wiki.archlinux.org/title/NVIDIA |
| Qwen3.8 GGUF file sizes only (community quant, `main` listing) | https://huggingface.co/unsloth/Qwen3.8-27B-GGUF |

No WARC archives or HTML body hashes were kept. If a URL later returns 404, the claim that
depends on it expires.

---

## Unverified leads

Last checked **2026-09-26** and not re-fetched. `workflow.md` marks anything that depends on
these as **Unverified**. Open the URL before acting on it.

| Claim in workflow.md | URL |
| --- | --- |
| A context window below 64K is a hard startup failure | https://github.com/NousResearch/hermes-agent/issues/53347 |
| Quickstart 64K instruction | https://hermes-agent.nousresearch.com/docs/getting-started/quickstart |
| `provider: custom`, `/model custom` auto-detect | https://hermes-agent.nousresearch.com/docs/integrations/providers and https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/faq.md |
| SearXNG optional skill (curl-direct fallback) | https://github.com/NousResearch/hermes-agent/blob/main/optional-skills/research/searxng-search/SKILL.md |
| Hermes 4.3 36B: Dec 2025 release, card, RefusalBench | https://nousresearch.com/introducing-hermes-4-3 and https://huggingface.co/NousResearch/Hermes-4.3-36B |
| Hermes 4.3 GGUF sizes (Q4_K_M 21.8 GB) | https://huggingface.co/NousResearch/Hermes-4.3-36B-GGUF/tree/main |
| Hermes 4.3 geometry (64 layers × 8 KV × 128) | https://huggingface.co/ByteDance-Seed/Seed-OSS-36B-Base/raw/main/config.json |
| Llama 3.3 70B geometry (80 × 8 × 128) | the model's published `config.json` |
| Qwen3-Coder-30B-A3B geometry (48 layers, 4 KV × 128) | https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct |
| Qwen3-Coder-30B-A3B SWE-bench Verified 50.3% | https://nebius.com/blog/posts/openhands-trajectories-with-qwen3-coder-480b |
| Official Qwen3-Coder family list (no 32B, no "30B Flash") | https://github.com/QwenLM/Qwen3-Coder |
| Ollama overhead (2–8% typical, 10–14% in one test) | https://inventivehq.com/blog/ollama-vs-llama-cpp-vs-lm-studio-benchmark |
| `auxiliary.session_search` config block | https://huggingface.co/docs/hub/en/agents-local |
| LanceDB memory plugin | https://www.lancedb.com/blog/semantic-memory-for-hermes-agent-with-lancedb |
| NotebookLM MCP is third-party browser automation | https://mixroute.ai/blog/hermes-agent-multi-agent-setup/ |
| Hermes 4 405B AA run page (linked from OpenRouter, never opened) | https://artificialanalysis.ai/models/hermes-4-llama-3-1-405b-reasoning |

## Not used on purpose

SEO and roundup sites were the source of earlier numbers that turned out to be wrong or couldn't
be traced: `codersera.com`, `kingy.ai`, `quesma.com`, `atomic.chat`, `willitrunai.com`,
`benchlm.ai`, `modelgrep.com`, `morphllm.com`, and a practitioner blog claiming
`auxiliary.session_search` was removed. Don't cite them for model facts.

---

## Known-false: do not reintroduce

Each of these appeared in earlier research for this repo and was shown to be wrong or
unsupported.

| Claim | Why it's wrong |
| --- | --- |
| "Qwen3-Coder 32B Instruct" as a local pick | The model doesn't exist (Hub: not found; not in the official family list). |
| 71.4% SWE-bench for a local Qwen3-Coder | Belongs to a different model. Qwen3-Coder-30B-A3B scores 50.3–51.6%. |
| Llama 3.3 70B IQ2_XXS as a 64K fallback on 24 GB | 20 GiB of KV plus ~21–23 GB of weights doesn't fit. |
| "Parallel/xAI" as a single Grok route | They are two different providers. xAI results are LLM-generated, not index-backed. |
| Hermes 4 405B as the planner | A generation behind on agentic and long-context benchmarks. Cheap is not a reason. |
| SearXNG as "air-gapped" | Self-hosted SearXNG still queries live engines. |
| "Deep Research" as a Hermes mode | No such product page. It is built from features (§3). |
| "Qwen3-Coder-Next 30B Flash" | Not in any primary source. |
| DeltaNet / linear-attention layers cost 0 memory | They hold a fixed state of ≈0.15 GiB for Qwen3.8-27B. |
| AA Intelligence Index "52 vs 38" for Qwen3.8-27B | Not on the model card and never traced to Artificial Analysis. |
| Gemma 4 26B-A4B "~17.5 GiB at 32K" or "149–194 tok/s" | Community blog figures, not reproduced. |
| "160M output tokens" for Qwen3.8-27B | Secondary citation, never traced. |
| Ollama "10–15% overhead" | Taken from one test; others measured 2–8%. |
| "Arch NVIDIA driver 555+ / CUDA 12.6" | Not what the current Arch wiki says; use the `nvidia-open` packages. |
| A 404 means an HF model is missing | Anonymous requests get 401 (see above). A TLS error proves nothing. |

---

## Open contradictions and gaps

- **Delegation cap:** the delegation guide says 10; the features overview and configuration
  reference say 3. Read the value on your build.
- **Hermes 4 405B tools:** its OpenRouter description says it supports tool use; a FAQ fragment on
  the same page says it doesn't. Only a live `scripts/test_tools.py --send` settles it.
- **Hermes 4.3 date:** the GGUF repo commits date from about Nov 2025, the Nous blog says December
  2025. Nothing in the workflow depends on this.
- **Throughput:** no tok/s figure in this repo was measured. Community figures vary up to ~2× with
  context length, quantisation and runtime build.
- **Frontier rankings** depend on the index version and reasoning effort, and shift weekly. Treat
  rank order as soft and the generation gap as hard.
- **`scripts/check_model_existence.py` has never completed from the authoring sandbox** (TLS EOF
  on egress). The pins above came from page fetches of the same API URLs.
