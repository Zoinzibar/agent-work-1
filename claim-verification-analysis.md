# Verification & analysis: "Hermes Agent on Arch / RTX 4090" research brief

**Verification date:** 2026-09-26 **·** **Revision:** v2 (post-review)
**Brief under review:** [`initial-agent-research.md`](initial-agent-research.md) (reproduced verbatim, now with a warning banner)
**Method:** every checkable claim was re-checked against primary sources where they exist — the official
Hermes Agent docs (`hermes-agent.nousresearch.com/docs`, including the `llms.txt` index), the Nous Research
release blog and Hugging Face model cards, the ByteDance `Seed-OSS-36B-Base` `config.json`, OpenRouter's
model/endpoint data, the Qwen3-Coder model card and GitHub repo, official GGUF file listings, and
Artificial Analysis-derived leaderboards. Secondary blogs were used only where no primary source exists and
are labelled as such.

> ## ⏳ Freshness line — read this before acting
> Model claims verified **2026-09-26**. The local-model tier changed **once during authoring** (Qwen3.8-27B
> superseded Qwen3.6-27B on 2026-08-14) and again under review. **Re-check §4 and §5 before you buy or
> download anything**; assume a ~6-week half-life for the specific model picks below. The framework and
> KV-cache sections (§2 F1–F16, §3.2, §3.3) are far more durable than the model picks.

> ## 📋 Revision note (v2) — response to independent review
> An independent re-check of this document (`review-of-pr-1.md`, PR #1 comment) confirmed 14 of 15
> spot-checked claims but requested changes on citation discipline, grading, and freshness. All ten of its
> suggested changes are applied here:
> 1. **Sources now carry URLs + access dates** (§7 rewritten as a table) — was the main blocker.
> 2. **M1 re-graded ❌ → ⚠️** ("four sizes from 14B to 405B" is literally true once the 36B is counted);
>    the headline error count is **3, not 4**.
> 3. **The ✅ column is split**: "verified as stated" vs "verified with material qualification", and the
>    qualified rows (F13, F16, M3, M7, M8, M10, M11, M12, M13, M16) now sit in the ⚠️ column where the
>    rubric puts them — the ⚠️ rows are F9, F10, F13, F16, M1, M3, M7, M8, M10, M11, M12, M13, M16.
>    **M8 is no longer ✅** — its own cited source contradicts the verdict.
> 4. **Local tier refreshed**: Qwen3.8-27B replaces Qwen3.6-27B; a release-date column is added; the
>    gpt-oss-20B age is flagged; the Qwen3-Coder-Next "30B Flash" question is closed (below).
> 5. §3.2's "explains three of the brief's four errors" → **one**; the GB/GiB sum in M4/§3.3 is corrected
>    (~39 GB, not 37.8); estimated vs computed KV rows are now labelled.
> 6. **M14's policy limb is cut** (it misread the RAM-spill policy and contradicted §4); the arithmetic
>    limb stands alone.
> 7. §3.4's Artificial Analysis numbers are pinned to index version + effort + date, and marked directional.
> 8. Unscored material is moved under a clearly-labelled "new findings — not part of the scorecard" part
>    (§5).
> 9. A warning banner plus `†` markers were added to `initial-agent-research.md`.
> 10. This freshness line.
>
> One correction to the review itself: it estimated ~19 ✅ / 9 ⚠️ / 3 ❌. My recount under the tightened
> rubric gives **17 ✅ / 13 ⚠️ / 3 ❌** — I applied its M8, M3, M7, F13 and superlative points more
> aggressively than its own estimate implies. Both are honest readings of the same evidence; the point the
> review makes — that the old 22/7/4 was a rubric artifact — is correct either way.

**Scorecard — 33 scored claims (+1 advisory row, not scored)**

| Verdict | Count | Share |
| --- | --- | --- |
| ✅ Verified as stated | 17 | 52% |
| ⚠️ Verified with material qualification / needs qualification | 13 | 39% |
| ❌ Incorrect | 3 | 9% |
| — Advisory, not scored | 1 | — |

**Of the claims that are wrong, all three are in model selection.** The framework half of the brief (F1–F16)
is in excellent shape: 11 of 16 verified as stated, 4 with qualification, 1 wrong. The errors that matter
are two load-bearing model picks — a local model that does not exist and a fallback that cannot hold a 64K
KV cache — plus one provider conflation. The brief's conclusion (hybrid local + cloud) survives; the
specific models do not.

---

## 1. Framework claims (Hermes Agent itself)

| # | Claim | Verdict | Evidence |
| --- | --- | --- | --- |
| F1 | Hermes Agent is an open-source agent framework by Nous Research running in terminal, desktop app, messaging platforms and IDEs, "same category as Claude Code and OpenClaw" | ✅ | The docs say exactly this, including the Claude Code / Codex / OpenClaw comparison and the ACP surface for VS Code / Zed / JetBrains |
| F2 | Works with any LLM provider, including local models | ✅ | Docs: Nous Portal, OpenRouter, OpenAI, Anthropic, Google, "or any OpenAI-compatible endpoint"; local via managed llama.cpp, Ollama, vLLM, llama.cpp server, SGLang, LocalAI |
| F3 | **Hard minimum of 64,000 tokens of context; smaller models are rejected at startup** | ✅ | Official quickstart: "set its context size to at least 64K"; Local Models page: "Every recommended model gets at least a 64K context window"; upstream issue #53347 confirms a hard failure, not a warning |
| F4 | Web search ships built in (not a custom skill); `hermes tools` → Web Search & Extract lets you pick a provider and stores the key/URL | ✅ | Official Web Search & Extract page |
| F5 | With no credentials, requests rotate across free tiers of **Exa, Parallel, Firecrawl, Keenable**, and a rate-limited request fails over to the next vendor | ✅ | Docs verbatim: round-robin keyless ring, "multi-hop, until one serves or all are throttled". Nuance the brief omits: this tier is *last-resort*, requires no user identifiers, and is vendor-rate-limited under burst load |
| F6 | Paid Nous Portal gives web search/extract through the Tool Gateway with no API key; `hermes setup --portal` enables all gateway tools at once | ✅ | Docs verbatim; gateway covers web search, image gen, TTS, browser automation |
| F7 | Exa = "neural search with semantic understanding, good for research and finding conceptually related content" | ✅ | Verbatim from the docs |
| F8 | "**Parallel/xAI routing** routes `web_search` through Grok's server-side `web_search` tool … returns top results as structured JSON" | ❌ | Conflated. They are two separate backends: **Parallel** is its own search/extract provider and keyless-ring member; **xAI (Grok)** is a search-only backend that runs Grok's server-side `web_search` on the Responses API, requires explicit `web.backend: "xai"` (deliberately *not* in the auto-detect chain), and — per the docs' own trust-model caveat — returns **LLM-generated** titles/descriptions/URL choice rather than index-backed results. For a citation-driven research workflow that caveat matters more than the JSON shape |
| F9 | For local-only/air-gapped setups, `hermes skills install official/research/searxng-search` | ⚠️ | The command is exact and the skill exists. But the framing is stale: SearXNG is now a **first-class built-in search backend** (`web.search_backend: "searxng"`), and the skill is an optional curl-direct fallback. "Air-gapped" is the wrong word: self-hosted SearXNG still queries live search engines, and it is search-only — `web_extract` needs a separate provider |
| F10 | Deep Research "isn't a separate product — it's Hermes's multi-step research mode" | ⚠️ | Reasonable shorthand, but there is **no named "Deep Research" feature or mode in the docs**. What exists is a composable capability set (delegation, execute_code, cron, MCP, memory, document reading) plus a community `deep-research` skill on the Skills Hub. Present it as *you compose it*, not as a switch you flip |
| F11 | Delegates & parallelises — spawns isolated subagents for parallel workstreams | ✅ | `delegate_task`. Only the final summary returns to the parent's context. (The docs contradict themselves on the default fan-out — Overview says 3, the Delegation guide says 10 — but the claim itself holds) |
| F12 | Programmatic Tool Calling via `execute_code` collapses multi-step pipelines into single inference calls | ✅ | Verbatim from the docs; intermediate tool results never enter the context window, only `print()` output does (timeout/`stdout` caps apply) |
| F13 | Research across your own documents; NotebookLM via MCP generates reports from your own sources | ⚠️ | Document reading/context files are native — that half is ✅. But NotebookLM is a **third-party MCP server** (`notebooklm-mcp-cli`), not a Nous integration, and it drives NotebookLM via **browser automation**; the community guides themselves recommend keeping a non-NotebookLM fallback. The brief presents it as a Hermes capability |
| F14 | Schedule recurring research on autopilot via built-in cron | ✅ | Native cron with natural-language scheduling + an official "Daily Briefing Bot" guide. Caveat no one mentions: scheduled work is delivered to messaging platforms, and each run eats full model cost |
| F15 | MCP connects to any MCP server, so you can bolt on arXiv, SEC filings, internal wikis | ✅ | Native MCP support; arXiv/SEC-style sources exist as community MCP servers/skills |
| F16 | Deep Research is far more token-hungry than a single search | ⚠️ | Directionally certain (multi-turn planning, one subagent context per workstream, long synthesis), and now supported by an independent data point — AA measured Qwen3.8-27B emitting 160M output tokens across its Intelligence Index testing vs a 43M median for comparable open-weight models — but the brief offers no quantification, so the claim is unquantified rather than verified |

---

## 2. Model claims

| # | Claim | Verdict | Evidence |
| --- | --- | --- | --- |
| M1 | "The current public family covers **four sizes from 14B to 405B**" | ⚠️ | **Re-graded from ❌.** The sentence counts 14B, 36B, 70B, 405B — four sizes spanning 14B to 405B — and the same sentence goes on to discuss the 36B, so it is literally true. The real defect is that it blurs two release generations (Hermes 4: 14B/70B/405B, late Aug 2025; Hermes 4.3: 36B, Dec 2025) and implies one coherent family. That is a qualification, not an error |
| M2 | Hermes 4.3 36B released **December 2025**, trained on the Psyche distributed network | ✅ | Nous blog: "December 2025", trained start-to-finish on Psyche (TP+DisTrO), 24 nodes, ~144k tok/s; HF card confirms |
| M3 | 36B "nearly matches the 70B at half the VRAM cost" | ⚠️ | Nous's own framing, true on benchmark averages and at short context — the rows M4/M5 already treat it as real. But it **breaks precisely at the 64K window you need**, because the 36B's KV cache is far larger (see §3.2). Marked ✅ in v1; that was too generous for a claim that fails on the one axis this user asked about |
| M4 | The 36B "does **not** comfortably fit on your single 24 GB card at good quality" | ✅ | Correct, and provable: Q4_K_M = **21.8 GB** + 16 GiB of KV cache at 64K (17.2 GB) = **~39 GB**. Q3_K_M + a heavily quantised KV cache lands ~22 GB — technically loadable, quality-degraded, zero headroom |
| M5 | Fits a two-GPU 4090 setup at 4-bit, or a single A100 80 GB at higher precision | ✅ | 2×24 GB handles 21.8 GB weights + 17.2 GB KV; Q8_0 is 38.4 GB and fits an A100 80 GB with 16 GiB KV (~55 GB). Full BF16 (72.3 GB) does *not* fit with a 64K KV cache |
| M6 | MATH-500 93.8 / MMLU 87.7 / BBH 86.4 / AIME 24 71.9 / GPQA-Diamond 65.5 | ✅ | Exact match to the Psyche column of the official benchmark table |
| M7 | RefusalBench 74.6% vs 59.5% for Hermes 4 70B; "answered 74.6% of questions that other aligned models refuse" | ⚠️ | Both numbers exact — but the comparison is **apples-to-oranges**: 74.6% is the **non-reasoning** 4.3 variant (4.3 reasoning = 72.29%), while 59.5% is the **70B reasoning** variant (70B non-reasoning = 49.07%). Read like-for-like the gap is 74.60 vs 49.07. The number is right; the implied comparison is not |
| M8 | "On raw frontier benchmarks Claude Opus still leads" | ⚠️ | **Re-graded from ✅ — v1's own evidence contradicted its verdict.** The ordering is index-dependent: one Sept-24 compilation has GPT-5.6 Sol 58.9 vs Claude Opus 5.5 57.6; an AA comparison page shows Opus 5 at 51 vs Sol 47; a Sept-22 round-up has Opus 5.5 at 58. The defensible version of the claim is "Claude Opus is at or near the frontier", not "leads". Note also the brief's model names are 2025-era |
| M9 | **"Qwen3-Coder 32B Instruct" Q4_K_M, ~55 tok/s @32K, 71.4% SWE-bench Verified, beats GPT-4o-mini on HumanEval+/SWE-bench Verified** | ❌ | **No such model exists.** The official Qwen3-Coder family is 480B-A35B, **30B-A3B**, and Qwen3-Coder-Next (80B-A3B); Qwen's own materials list 14B/8B/7B/**32B**/4B among *non*-official sizes, and "Qwen3-Coder-32B" appears only in low-quality community blogs. The real 30B-A3B (30.5B total / 3.3B active, 48 layers, 32 Q-heads / **4 KV heads**, 262K ctx) scores **50.3%** SWE-bench Verified (OpenHands; Nebius) / 51.6% Qwen-reported — not 71.4%. That 71.4% figure matches DeepSeek V4 Pro, and the "32B" is likely confused with Qwen2.5-Coder-32B (a different, 128K-context dense family) |
| M10 | Gemma 4 26B-A4B — Q4_K_M, MoE, ~16 GB, ~85 tok/s, 256K context, "best overall" | ⚠️ | Model is real (Apr 2026, Apache 2.0, 25.2B total / 3.8B active, 262K ctx, native function calling). ~16 GB is right (measured GGUF 15.64 GiB; 17.5 GiB VRAM at 32K). But **~85 tok/s is a bandwidth *estimate* from a hardware-guidance site**; measured 4090 reports are 149–194 tok/s. The number is directionally conservative but wrongly attributed. The superlative "best overall" is **not scored** — it is subjective, and the same standard that excluded M18 applies |
| M11 | Qwen 3.6 27B = best dense reasoning model | ⚠️ | The model is real and strong (Apr 22, 2026; 262K ctx, vision, Apache 2.0; Q4_K_M ≈ 16.8 GB; ~43 tok/s measured on a 4090 in a community run). But it is **superseded** — see §4 — and "best" is not scored. Graded on existence + fit in v1, which was inconsistent with excluding M18 |
| M12 | gpt-oss 20B "praised for the cleanest tool calls", ~14 GB, lots of headroom | ⚠️ | Model qualifies and fits with the most headroom of anything listed (~12–14 GB MXFP4, 131K ctx, Aug 2025). But "cleanest tool calls" is sentiment, not a benchmark: τ-bench Retail 54.8% vs 67.8% for gpt-oss-120B. It is a good *cheap* tool-caller, not the best one — and it is now a 13-month-old model |
| M13 | llama.cpp for solo use, vLLM or TensorRT-LLM for concurrency; "Ollama is fine but loses 10–15% throughput" | ⚠️ | Hermes's own docs name vLLM/SGLang for production serving (never TensorRT-LLM) and ship a *managed llama.cpp runtime* for local use; Ollama's measured overhead was 10.3% on an RTX 5060 Ti and 14% on an M3 Max in one 2026 test, but 2–8% in several others — "10–15%" is the pessimistic tail, not the central estimate |
| M14 | **Llama 3.3 70B IQ2_XXS (2.4 bpw) fits in 23.1 GB and delivers ~14 tok/s — "usable"** under the 64K floor | ❌ | **The arithmetic alone is decisive.** Llama-3.3-70B has 80 layers × 8 KV heads × 128 head_dim, so its KV cache costs **320 KiB/token** — **20 GiB at 64K** — on top of ~21–23 GB of weights. It does not fit a 24 GB card, at any speed. *(v1 also dismissed it on "sub-4-bit is unsupported policy" grounds; that limb is **cut** — see §3.3 — but the verdict is unchanged)* |
| M15 | Custom endpoint config; `provider: custom` is first-class, not an alias; `/model custom` auto-detects a single loaded model; works with Ollama, vLLM, llama.cpp server, SGLang, LocalAI | ✅ | Verbatim from the providers doc and FAQ |
| M16 | Embedding/session-search sidecar via `auxiliary: session_search` pointing at a local embedding endpoint | ⚠️ | The exact config block is documented by the Hugging Face "Local Agents with llama.cpp" guide for Hermes. But it is version-sensitive: a Sept-2026 practitioner reference reports the auxiliary `session_search` LLM slot no longer exists in current builds (session search returns DB content directly via SQLite FTS5) and that semantic recall now flows through **memory-provider plugins** (LanceDB, Honcho, Mem0, …) that accept any OpenAI-compatible embedding endpoint. Verify against your installed version before wiring it |
| M17 | Hermes 4 405B on OpenRouter: $1/$3 per M tokens, 131,072 context, "few-dollars" daily Deep Research | ✅ (facts) | OpenRouter confirms $1/$3, 131K, served by Nebius Token Factory. Throughput is window-dependent — the page has shown both ~28 and ~33 tok/s P50. A heavy run (~500K in / 100K out) ≈ $0.80, so the cost estimate is fair. The *capability* assumption behind it is the weak link → see §5.1 |
| M18 | Start local-only; add the cloud planner only when quality plateaus | — | Advisory, not a factual claim — **not scored**. Worth flagging that it sequences the *hardest* part (top-level multi-hop planning/synthesis) last, which is where a 24 GB local model is most likely to disappoint |

---

## 3. Verified findings and corrections

*(§3.1–§3.4 are verification of the brief. §5 and §6 are new findings and are **not** part of the scorecard.)*

### 3.1 The recommended local model does not exist

"Qwen3-Coder 32B Instruct" is not an official Qwen release, and the 71.4% SWE-bench Verified figure
attached to it belongs to a different model (it tracks DeepSeek V4 Pro; Qwen3-Coder-Next lands at
~70.6–71.3%). Real, checkable Qwen3-Coder options:

| Model | Architecture | Context | SWE-bench Verified | Local feasibility (24 GB) |
| --- | --- | --- | --- | --- |
| Qwen3-Coder-480B-A35B | 480B MoE / 35B active | 256K | 69.6% (Qwen) | ❌ data-centre only |
| Qwen3-Coder-30B-A3B | 30.5B MoE / 3.3B active | 262K | 50.3–51.6% | ✅ Q4_K_M ≈ 18.6 GB; 6 GiB KV at 64K |
| Qwen3-Coder-Next | 80B MoE / 3B active (hybrid attn) | 256K | ~70.6–71.3% | ⚠️ Q4_K_M ≈ 48.7 GB → needs 2×24 GB or offload |
| Qwen2.5-Coder-32B (if that's what was meant) | 32B dense | 128K | ~62.5% (community) | ✅ ~19 GB, but a 2024-generation model |

**Closed open question:** the reviewer flagged a possible "Qwen3-Coder-Next 30B Flash" at ~18 GB as the
highest-value unconfirmed lead. I could not confirm it either: Qwen's official repository lists exactly
480B-A35B, 30B-A3B and Next, with no "30B Flash" variant, and the only occurrences of the phrase are user
comments ("Flash-speed tuned for coding"), not a product name. **Treat it as unconfirmed — do not plan
around it** unless it appears on the official Qwen3-Coder repo.

The brief's underlying advice is sound: use a **30B-class MoE with ~3B active parameters** for tool-calling
work on a 24 GB card. The name and the score were the problem.

### 3.2 The KV cache, not the weights, is what the 64K floor really costs you

The brief treats 64K context as a soft tax on VRAM headroom. It is the dominant term. For a standard
grouped-query attention model:

```
KV bytes/token = 2 (K+V) × layers × kv_heads × head_dim × bytes_per_element   [2 B at fp16]
```

| Model | Geometry | KV per token (fp16) | KV at 64K | Basis |
| --- | --- | --- | --- | --- |
| Hermes 4.3 36B (Seed-OSS-36B base) | 64 layers × 8 KV × 128 | 256 KiB | **16 GiB** | computed |
| Llama 3.3 70B | 80 layers × 8 KV × 128 | 320 KiB | **20 GiB** | computed |
| Qwen3-Coder-30B-A3B | 48 layers × 4 KV × 128 | 96 KiB | 6 GiB | computed |
| Qwen3.8-27B | 16 full-attn layers × 4 KV × 256 | 64 KiB | ~4 GiB (≈2.3 GB per 32K, measured) | computed + measured |
| Gemma 4 26B-A4B | hybrid attention | — | ~small | estimated, not derived — treat as indicative |

(Seed-OSS-36B figures read directly from `ByteDance-Seed/Seed-OSS-36B-Base`'s `config.json`:
`num_hidden_layers: 64`, `num_key_value_heads: 8`, `head_dim: 128`, `max_position_embeddings: 524288`.)

This table is decisive for **one** of the brief's three errors: **M14**, the IQ2 70B fallback — it cannot
hold a 64K KV cache at any quantisation. *(v1 claimed it explained three of four; that was wrong — the
other errors are F8, a provider conflation, and M9, a model that does not exist, and neither is a
memory question.)* The table also *supports* M4/M5, which were already graded ✅, and it is the reason the
refreshed local picks in §6 work where the 36B does not.

**Unit note (corrected):** the Hermes 4.3 arithmetic mixes units. GGUF file sizes are published in decimal
GB; llama.cpp allocates in GiB. 21.8 GB + 16 GiB (= 17.2 GB) ≈ **39 GB**, not the ~37.8 GB v1 printed;
~37.8 only works if the weights are read as GiB. No conclusion changes — both readings are far over 24 GB —
but the sum is now stated in one unit.

### 3.3 The Hermes 4.3 36B verdict is right — and the v1 justification for the 70B was not

The conclusion "does not comfortably fit your single 24 GB card at good quality" is correct, the benchmark
set is copied accurately, and the two-GPU / A100-80GB statements hold. The reason is 21.8 GB of Q4 weights
plus a 16 GiB KV cache at the mandatory 64K window (~39 GB total).

**Cut from v1:** I had also dismissed the IQ2 70B on policy grounds — "Hermes's managed runtime never offers
builds smaller than 4-bit, so you cannot lawfully fit it through the supported path". That was doubly wrong.
The Local Models page says the overflow is *deliberately placed in system RAM* ("a machine that can't run
the 4-bit build **spilled to system RAM**…"), and the catalog renders that state as amber "Uses system
RAM" — **RAM spill is a supported path**. What the runtime refuses is *sub-4-bit quants*, which is a
different claim. And in any case the brief recommends a **custom endpoint** (Ollama/llama.cpp/vLLM), where
no managed-runtime quantisation policy applies. The arithmetic in §3.2 is sufficient on its own, and it is
now the only reason given. This also removes the v1 self-contradiction between §3.3 (managed path can't
spill) and §6 (managed path spills expert weights to protect context) — the latter was correct.

### 3.4 The weakest link: Hermes 4 405B as the "planner brain"

**Directional conclusion, not a pinned measurement.** Hermes 4 405B is an August 2025 fine-tune of
Llama-3.1-405B. The panel scores below are as published on OpenRouter's model page (which mirrors
Artificial Analysis results) **as of 2026-09-26**, reasoning mode, and AA's index has been revised several
times (v4.1 → v4.3.x), with effort settings moving scores substantially between boards. Quote them as
indicative of a *generation gap*, not as a precise ranking:

| Benchmark (Hermes 4 405B, reasoning) | Score |
| --- | --- |
| Terminal-Bench Hard (agentic coding / terminal) | 11.4% |
| τ²-Bench Telecom (dual-control tool use) | 22.2% |
| AA-LCR (long-context reasoning) | 22.3% |
| HLE | 10.9% |
| AA-Omniscience non-hallucination rate | 5.5% |

For a workload whose stated real benchmark is "can the model read a file, call the terminal, preserve the
requested format, recover from a failed tool, and complete a second turn without drifting", those are the
wrong numbers — and long-context reasoning is the one that matters most for cross-source synthesis.
Meanwhile open-weight models now score far higher on the same instrument (DeepSeek V4 Pro 0813 53.2,
GLM-5.3 ~45, Kimi K3 ~44 on the compilations checked 2026-09-26), and frontier models sit in the high 50s.
The OpenRouter page's own traffic data reinforces this: the top apps sending tokens to Hermes 4 405B are
roleplay front-ends, not agent harnesses.

Keep the *architecture* of the recommendation (offload top-level planning and synthesis to a cloud model);
change the *model*. If you specifically want the Hermes lineage, route Hermes 4.3 36B for short-context work
and use a current tool-calling frontier/adjacent model as the planner. The brief's "few-dollars daily" cost
estimate is fair at $1/$3 — but that pricing is not special in 2026.

---

## 4. What the scorecard did not cover

Everything below is a **new finding or recommendation, not a scored claim**. It was gathered during
verification but never graded, and it should be read with that discount.

- **Web results are budgeted, not summarised.** `web_extract` truncates deterministically at 15,000
  characters by default (`web.extract_char_limit`, clamped 2,000–500,000) and writes the full text to disk
  with a footer telling the agent how to page through it. Long-form research needs that limit raised or an
  `execute_code` stage, or the agent will work from head/tail excerpts.
- **Duplicate searches are coalesced and cached** — identical concurrent queries from a subagent fan-out
  collapse into one backend request, and extracted URLs are cached under `~/.hermes/cache/web/` across CLI,
  gateway, cron and subagent processes. Good for cost, but "N independent subagents" are less independent
  than they look.
- **The keyless ring is a rescue path, not a plan** — explicitly last-resort, rate-limited under burst load,
  and even keyed/managed backends do a one-shot non-sticky rescue to it on failure. Budget a keyed provider
  (Firecrawl 500 credits/mo free tier, or self-hosted SearXNG for search + a keyed extractor, since SearXNG
  cannot extract).
- **Deep research has no single switch.** The docs expose delegation, `execute_code`, cron, memory, MCP and
  document reading as separate features.
- **The embedding sidecar is version-sensitive.** Plan for the memory-provider path (LanceDB/Honcho with a
  local OpenAI-compatible embedding endpoint such as `nomic-embed-text` or `EmbeddingGemma-300M`) and treat
  the `auxiliary.session_search` block as a check-your-version detail.
- **A local-model age check is now part of the rubric.** A reviewer pointed out the obvious asymmetry: this
  document criticises the brief for recommending a 2025-generation model, while itself listing gpt-oss-20B
  (Aug 2025). §6 now carries release dates.

## 5. Corrected local shortlist for one RTX 4090 (24 GB) under Hermes's 64K floor

**Not part of the scorecard — these are recommendations, refreshed 2026-09-26, and they decay.**

| Model | Released | Type | Q4 weights | Context | Fits 64K on one 4090? | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| **Qwen3.8-27B** ⭐ | 2026-08-14 | dense 27B VLM, hybrid attn (48 DeltaNet + 16 full) | ~17–17.8 GB | 262K native, 1M via YaRN | ✅ 17.8 GB + ~4.6 GB f16 KV ≈ 22–23 GB; an independent quantisation study states Q4_K_M "fits on a 24 GB card… still leaving room for about 64k tokens of context" | **New top pick.** AA Intelligence Index **52** (v4.1.1, nine evals) vs **38** for Qwen3.6-27B at identical size — a 14-point post-training jump. Apache 2.0, vision. Reported 4090 decode ~50 tok/s plain, ~40 tok/s at 128K depth, up to ~149 tok/s with MTP3. Caveat: defaults to *xhigh* reasoning effort and over-thinks — budget tokens |
| Gemma 4 26B-A4B | 2026-04 | MoE, ~3.8B active | 15.6 GiB | 256K | ✅ ~17.5 GiB VRAM at 32K; 192K consumed within 20.9 GB in a measured run | Measured 149–194 tok/s; native function calling; Apache 2.0; best speed/headroom balance |
| Qwen3-Coder-30B-A3B | 2025-07 | MoE, 3.3B active | ~18.6 GB | 262K | ⚠️ tight — 6 GiB fp16 KV at 64K (use q8_0 KV) | Purpose-built tool-call format; 50.3–51.6% SWE-bench Verified. Now an older generation |
| gpt-oss-20B | 2025-08 | MoE, ~3.6B active | ~12–14 GB | 131K | ✅ most headroom | τ-bench Retail 54.8%; leaves room for an embedding sidecar. Kept for headroom only — 13 months old |
| ~~Qwen3.6-27B~~ | 2026-04-22 | dense 27B | 16.8 GB | 262K | ✅ | **Superseded by Qwen3.8-27B** at the same size, licence and VRAM. This was v1's recommendation and it was six weeks stale on arrival |
| Hermes 4.3 36B | 2025-12 | dense 36B | 21.8 GB | 512K | ❌ 21.8 GB + 16 GiB KV ≈ 39 GB | 2×24 GB or bust; Q8_0 on an 80 GB card |
| Llama 3.3 70B (any quant) | 2024-12 | dense 70B | ~40 GB at 4-bit | 128K | ❌ | The 20 GiB KV cache at 64K is fatal on 24 GB regardless of quantisation |

**Two practical notes.** First, Hermes's managed local runtime already enforces most of this: it prices
every catalog model against your GPU *including* context/KV state, picks the highest-quality ≥4-bit build
that fits, guarantees ≥64K, grows the window as needed, and spills to system RAM (expert weights first,
never the attention cache) when a model overflows — so an oversized model can still run, slowly, rather
than being refused. Second, if you drive llama.cpp/vLLM yourself, set the context explicitly
(`--ctx-size 65536`) and remember Hermes's own warning for Ollama: its `/api/show` reports the model's
*maximum* context, not the effective `num_ctx`, so set `OLLAMA_CONTEXT_LENGTH=64000` (or equivalent) and
match it in `config.yaml`.

## 6. Corrected recommended stack

1. **Local tier** — **Qwen3.8-27B Q4_K_M** as the default (best local quality per GB on current
   independent numbers, ~22–23 GB at a real 64K window). **Gemma 4 26B-A4B** when throughput matters more
   than depth (measured ~150–190 tok/s, huge context ceiling). Qwen3-Coder-30B-A3B only if you specifically
   need its tool-call format and accept an older generation.
2. **Planner/synthesis tier** — a current (2026) frontier or frontier-adjacent model with verified tool
   calling, *not* Hermes 4 405B (§3.4). If staying in the Hermes lineage matters, use Hermes 4.3 36B
   (short context) or Portal-routed models; keep a low-refusal model available as a *policy* escape hatch,
   not as the reasoning engine. Verify that your gateway route actually accepts `tools` before committing.
3. **Web search** — keyed Firecrawl (500 credits/mo free) or self-hosted SearXNG for search plus a keyed
   extractor; keep the keyless ring as automatic failover, and remember xAI search results are
   model-generated, so don't cite them blind. With a paid Nous Portal subscription,
   `hermes setup --portal` is the lowest-friction path.
4. **Memory** — a memory provider with a local OpenAI-compatible embedding endpoint; treat
   `auxiliary.session_search` as version-dependent.
5. **Engine** — Hermes's managed llama.cpp runtime for simplicity; llama.cpp server for control;
   vLLM/SGLang only for concurrent serving (Hermes docs' own recommendation).
6. **Sequencing** — start local, but validate the *planner* path early with real multi-hop research tasks;
   the local model is the part of this stack least likely to be the bottleneck.

---

## 7. Residual uncertainty

- **Hermes catalog specifics change fast.** Whether the managed runtime currently certifies
  Qwen3.8-27B / Gemma 4 26B-A4B at ≥64K *on your exact card + driver* should be checked in
  Settings → Providers → Local Models on your install; the docs describe the policy, not the row list.
- **Throughput numbers are community-sourced** and vary up to ~2× with context length, quantisation, KV
  quantisation and runtime build. The 4090 figures here are reports, not my measurements.
- **One docs contradiction inside Hermes itself:** the Features Overview says "3 concurrent subagents by
  default" while the Delegation guide says 10. Check `delegation.max_concurrent_children` on your build.
- **One OpenRouter contradiction:** the Hermes 4 405B model page's description says it supports function
  calling and tool use; a FAQ fragment on the same page says it does not accept tools. Confirm with a live
  request before depending on it either way.
- **Frontier rankings are index- and effort-dependent** and shift weekly (see M8). Treat the *rank ordering*
  as soft, the *generation gap* as hard.
- **Minor date discrepancy:** the Hermes 4.3 GGUF repo shows commit dates ~10 months before Sept 2026
  (≈Nov 2025) while the Nous blog says December 2025; the blog is treated as authoritative here.
- **Qwen3.8-27B KV figures** blend a computed geometry (16 full-attention layers × 4 KV heads × 256) with a
  measured ~2.3 GB per 32K tokens; the two agree closely, but they are different methods.
- **The Qwen3-Coder-Next "30B Flash" variant could not be confirmed from any primary source** and is
  treated as non-existent pending an official listing.

---

## 8. Sources (all URLs accessed 2026-09-26)

### Hermes Agent — official documentation

| Source | URL |
| --- | --- |
| Docs index (`llms.txt`) | https://hermes-agent.nousresearch.com/docs/llms.txt |
| Web Search & Extract (backends, keyless ring, extract budget, caching, xAI caveat) | https://hermes-agent.nousresearch.com/docs/user-guide/features/web-search |
| Local Models (64K guarantee, ≥4-bit policy, RAM spill, context growth) | https://hermes-agent.nousresearch.com/docs/user-guide/local-models |
| Quickstart (64K instruction) | https://hermes-agent.nousresearch.com/docs/getting-started/quickstart |
| Providers / Integrations (Portal, Tool Gateway, custom endpoints) | https://hermes-agent.nousresearch.com/docs/integrations/providers |
| FAQ (custom endpoint, `/model custom` auto-detect) | https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/faq.md |
| Features Overview (subagent count = 3) | https://hermes-agent.nousresearch.com/docs/user-guide/features/overview |
| Subagent Delegation (subagent count = 10, constraints) | https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation |
| Code Execution / Programmatic Tool Calling | https://hermes-agent.nousresearch.com/docs/user-guide/features/code-execution |
| SearXNG optional skill | https://github.com/NousResearch/hermes-agent/blob/main/optional-skills/research/searxng-search/SKILL.md |
| Upstream issue #53347 — 64K is a hard failure | https://github.com/NousResearch/hermes-agent/issues/53347 |

### Nous Research — models

| Source | URL |
| --- | --- |
| "Introducing Hermes 4.3" blog (Dec 2025, Psyche, 144k tok/s, 24 nodes) | https://nousresearch.com/introducing-hermes-4-3 |
| HF card `Hermes-4.3-36B` (benchmark + RefusalBench tables, tool-call format) | https://huggingface.co/NousResearch/Hermes-4.3-36B |
| HF GGUF file listing (Q3_K_M 17.6 GB; **Q4_K_M 21.8 GB**; Q5 25.6 GB; Q8_0 38.4 GB; BF16 72.3 GB) | https://huggingface.co/NousResearch/Hermes-4.3-36B-GGUF/tree/main |
| Hermes 4 405B on OpenRouter ($1/$3, 131K, Nebius, AA panel) | https://openrouter.ai/nousresearch/hermes-4-405b |
| Hermes 4 family sizes 14B/70B/405B, Aug 2025 | https://aiwiki.ai/wiki/hermes_4 |

### Architectures / KV arithmetic

| Source | URL |
| --- | --- |
| `ByteDance-Seed/Seed-OSS-36B-Base` `config.json` (64 layers, 8 KV heads, head_dim 128, 512K) | https://huggingface.co/ByteDance-Seed/Seed-OSS-36B-Base/raw/main/config.json |
| Llama-3.1/3.3-70B GQA geometry (80 layers, 8 KV heads, 128) | via published model configs |

### Qwen

| Source | URL |
| --- | --- |
| Qwen3-Coder blog (Jul 22 2025; 480B-A35B; 256K→1M) | https://qwenlm.github.io/blog/qwen3-coder/ |
| HF card `Qwen3-Coder-30B-A3B-Instruct` (30.5B/3.3B, 48 layers, 32 Q / 4 KV heads, 262,144 ctx) | https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct |
| QwenLM/Qwen3-Coder repo — official family list (no "30B Flash") | https://github.com/QwenLM/Qwen3-Coder |
| Non-official size check (14B/8B/7B/32B/4B not official) | https://www.qwen3coder.com/ |
| Nebius OpenHands writeup (30B-A3B = 50.3% SWE-bench Verified) | https://nebius.com/blog/posts/openhands-trajectories-with-qwen3-coder-480b |
| Qwen3-Coder-Next Q4_K_M ≈ 48.8 GB | https://willitrunai.com/models/qwen-3-coder-next |
| Qwen3.8-27B release + AA 52 vs 38 + overthinking | https://codersera.com/blog/qwen-3-8-27b-complete-guide-2026/ |
| Qwen3.8-27B specs (64 layers; 48 DeltaNet + 16 full-attn; 24 Q / 4 KV × 256; 262,144 native) | https://kingy.ai/blog/qwen3-8-27b-specs-benchmarks-local-hardware/ |
| Qwen3.8-27B local hardware ladder + "~64KB BF16 KV per token" | https://kingy.ai/blog/qwen3-8-27b-local-hardware-requirements/ |
| Qwen3.8-27B quantisation study (Q4_K_M 17 GB fits a 4090 with ~64K context; F16 KV ≈ 2.3 GB/32K) | https://quesma.com/blog/qwen38-27b-quantizations-benchmarked/ |
| Qwen3.8-27B on one 4090 (MTP3 decode, depth sweep, E8 4-bit KV) | https://github.com/sergiuszm/ninfer-4090 |
| Simon Willison on Qwen3.8-27B AA score | https://simonwillison.net/2026/Aug/17/qwen-38-27b-scores-52/ |
| VentureBeat: AA 52, Agentic Index 51, 160M output tokens | https://venturebeat.com/technology/qwen3-8-27b-runs-frontier-class-coding-agents-and-reasoning-locally-no-cloud-api-required |
| Qwen3.6-27B specs/VRAM | https://willitrunai.com/blog/qwen-3-6-27b-vram-requirements |

### Other local models / engines

| Source | URL |
| --- | --- |
| Gemma 4 26B-A4B (Apr 2026, 25.2B/3.8B active, 262,144 ctx, function calling) | https://openrouter.ai/google/gemma-4-26b-a4b-it:free |
| Gemma 4 26B-A4B measured 4090 GGUF run (15.64 GiB, 17,572 MiB @32K, 194.1 tok/s) | https://atomic.chat/blog/guides/best-local-llms-for-rtx-4090 |
| gpt-oss-20B τ-bench Retail 54.8% / Airline 38.0% | https://docs.api.nvidia.com/nim/reference/openai-gpt-oss-20b |
| Ollama vs llama.cpp overhead (10.3% / 14% vs 2–8%) | https://inventivehq.com/blog/ollama-vs-llama-cpp-vs-lm-studio-benchmark |

### Ecosystem / third-party

| Source | URL |
| --- | --- |
| HF "Local Agents with llama.cpp" (Hermes custom endpoint + `auxiliary.session_search`) | https://huggingface.co/docs/hub/en/agents-local |
| Practitioner's Reference (auxiliary slot removals, session search behaviour) | https://blakecrosley.com/guides/hermes |
| LanceDB semantic-memory plugin | https://www.lancedb.com/blog/semantic-memory-for-hermes-agent-with-lancedb |
| NotebookLM MCP setup | https://mixroute.ai/blog/hermes-agent-multi-agent-setup/ |

### Leaderboards

| Source | URL |
| --- | --- |
| Artificial Analysis changelog (index versions v4.1 → v4.3.x) | https://artificialanalysis.ai/changelog |
| AA Intelligence Index compilation, Sept 24 2026 (Sol 58.9 / Opus 5.5 57.6) | https://benchlm.ai/benchmarks/artificialanalysis |
| Sept 2026 leaderboard + open-weight standings | https://modelgrep.com/leaderboard |
| Coding/agentic round-up incl. GLM-5.3 / Kimi K3 standings | https://www.morphllm.com/best-ai-model-for-coding |
