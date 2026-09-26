# Verification & analysis: "Hermes Agent on Arch / RTX 4090" research brief

**Verification date:** 2026-09-26
**Brief under review:** [`initial-agent-research.md`](initial-agent-research.md) (reproduced as received)
**Method:** every checkable claim was re-checked against primary sources where they exist — the official
Hermes Agent docs (`hermes-agent.nousresearch.com/docs`, including the `llms.txt` index and raw pages), the
Nous Research release blog and Hugging Face model cards, the ByteDance `Seed-OSS-36B-Base` `config.json`,
OpenRouter's model/endpoint data, the Qwen3-Coder model card and GitHub repo, official GGUF file listings,
and Artificial Analysis-derived leaderboards. Secondary blogs were used only where no primary source exists,
and are labelled as such.

**Scorecard — 33 scored claims**

| Verdict | Count | Share |
| --- | --- | --- |
| ✅ Verified as stated | 22 | 67% |
| ⚠️ Partially correct / needs material qualification | 7 | 21% |
| ❌ Incorrect | 4 | 12% |

The framework half of the brief is in excellent shape: nearly every Hermes Agent behaviour it describes
checks out almost word-for-word against the docs. **The errors are concentrated in the model-selection half,
and two of them are load-bearing**: the single best local model it recommends does not exist, and its
"70B at IQ2 is usable" fallback fails on KV-cache arithmetic. Its conclusion — hybrid local + cloud
planner — survives, but the specific picks need to be replaced.

---

## 1. Framework claims (Hermes Agent itself)

| # | Claim | Verdict | Evidence |
| --- | --- | --- | --- |
| F1 | Hermes Agent is an open-source agent framework by Nous Research running in terminal, desktop app, messaging platforms and IDEs, "same category as Claude Code and OpenClaw" | ✅ | The docs say exactly this, including the Claude Code / Codex / OpenClaw comparison and the ACP surface for VS Code / Zed / JetBrains |
| F2 | Works with any LLM provider, including local models | ✅ | Docs: Nous Portal, OpenRouter, OpenAI, Anthropic, Google, "or any OpenAI-compatible endpoint"; local via managed llama.cpp, Ollama, vLLM, llama.cpp server, SGLang, LocalAI |
| F3 | **Hard minimum of 64,000 tokens of context; smaller models are rejected at startup** | ✅ | Official quickstart: "set its context size to at least 64K"; the Local Models page: "Every recommended model gets at least a 64K context window"; upstream issue #53347 confirms it is a hard failure, not a warning |
| F4 | Web search ships built in (not a custom skill); `hermes tools` → Web Search & Extract lets you pick a provider and stores the key/URL | ✅ | Official Web Search & Extract page |
| F5 | With no credentials, requests rotate across free tiers of **Exa, Parallel, Firecrawl, Keenable**, and a rate-limited request fails over to the next vendor | ✅ | Docs verbatim: round-robin keyless ring, "multi-hop, until one serves or all are throttled". Nuance the brief omits: this tier is *last-resort*, requires no user identifiers, and is vendor-rate-limited under burst load |
| F6 | Paid Nous Portal gives web search/extract through the Tool Gateway with no API key; `hermes setup --portal` enables all gateway tools at once | ✅ | Docs verbatim; gateway covers web search, image gen, TTS, browser automation |
| F7 | Exa = "neural search with semantic understanding, good for research and finding conceptually related content" | ✅ | Verbatim from the docs |
| F8 | "**Parallel/xAI routing** routes `web_search` through Grok's server-side `web_search` tool … returns top results as structured JSON" | ❌ | Conflated. They are two separate backends: **Parallel** is its own search/extract provider and keyless-ring member; **xAI (Grok)** is a search-only backend that runs Grok's server-side `web_search` on the Responses API, requires explicit `web.backend: "xai"` (it is deliberately *not* in the auto-detect chain), and — per the docs' own trust-model caveat — returns **LLM-generated** titles/descriptions/URL choice rather than index-backed results. For a citation-driven research workflow that caveat matters more than the JSON shape |
| F9 | For local-only/air-gapped setups, `hermes skills install official/research/searxng-search` | ⚠️ | The command is exact and the skill exists. But the framing is stale: SearXNG is now a **first-class built-in search backend** (`web.search_backend: "searxng"`), and the skill is an optional curl-direct fallback. "Air-gapped" is the wrong word: self-hosted SearXNG still queries live search engines, and it is search-only — `web_extract` needs a separate provider |
| F10 | Deep Research "isn't a separate product — it's Hermes's multi-step research mode" | ⚠️ | Reasonable shorthand, but there is **no named "Deep Research" feature or mode in the docs**. What exists is a composable capability set (delegation, execute_code, cron, MCP, memory, document reading) plus a community `deep-research` skill on the Skills Hub. Present it as *you compose it*, not as a switch you flip |
| F11 | Delegates & parallelises — spawns isolated subagents for parallel workstreams | ✅ | `delegate_task`. Note: the docs contradict each other on the default fan-out — the Features Overview says 3 concurrent subagents, the Delegation guide says 10 (`delegation.max_concurrent_children`). Only the final summary returns to the parent's context |
| F12 | Programmatic Tool Calling via `execute_code` collapses multi-step pipelines into single inference calls | ✅ | Verbatim from the docs; intermediate tool results never enter the context window, only `print()` output does (timeout/`stdout` caps apply) |
| F13 | Research across your own documents; NotebookLM via MCP generates reports from your own sources | ✅ with caveat | Document reading/context files are native. NotebookLM is a **third-party MCP server** (`notebooklm-mcp-cli`), not a Nous integration, and it drives NotebookLM via browser automation — the community guides themselves recommend keeping a non-NotebookLM fallback |
| F14 | Schedule recurring research on autopilot via built-in cron | ✅ | Native cron with natural-language scheduling + an official "Daily Briefing Bot" guide. Caveat no one mentions: scheduled work is delivered to messaging platforms, and each run eats full model cost |
| F15 | MCP connects to any MCP server, so you can bolt on arXiv, SEC filings, internal wikis | ✅ | Native MCP support; arXiv/SEC-style sources exist as community MCP servers/skills |
| F16 | Deep Research is far more token-hungry than a single search | ⚠️ | Directionally certain (multi-turn planning, one subagent context per workstream, long synthesis), but no vendor quantification exists and the brief gives none. Treat as a design constraint, not a measured fact |

---

## 2. Model claims

| # | Claim | Verdict | Evidence |
| --- | --- | --- | --- |
| M1 | "The current public family covers **four sizes from 14B to 405B**" | ❌ | Hermes 4 shipped in **three** sizes — 14B, 70B, 405B (late Aug 2025; 14B on Qwen3-14B, 70B/405B on Llama 3.1). Hermes 4.3 adds a 36B checkpoint (Seed-OSS-36B base). "Four sizes from 14B to 405B" is not a thing |
| M2 | Hermes 4.3 36B released **December 2025**, trained on the Psyche distributed network | ✅ | Nous blog: "December 2025", trained start-to-finish on Psyche (TP+DisTrO), 24 nodes, ~144k tok/s; HF card confirms |
| M3 | 36B "nearly matches the 70B at half the VRAM cost" | ✅ with caveat | Nous's own framing, true on benchmark averages and at short context. It breaks precisely at the 64K window you need, because the 36B's KV cache is far larger (see §3) |
| M4 | The 36B "does **not** comfortably fit on your single 24 GB card at good quality" | ✅ | Correct, and provable: Q4_K_M = **21.8 GB** + 16 GiB of KV cache at 64K = ~37.8 GB. Q3_K_M + a heavily quantised KV cache lands ~22 GB — i.e. technically loadable, quality-degraded, zero headroom |
| M5 | Fits a two-GPU 4090 setup at 4-bit, or a single A100 80 GB at higher precision | ✅ | 2×24 GB handles 21.8 GB weights + 16 GiB KV; Q8_0 is 38.4 GB and fits an A100 80 GB with 16 GiB KV (~54 GB). Full BF16 (72.3 GB) does *not* fit with a 64K KV cache |
| M6 | MATH-500 93.8 / MMLU 87.7 / BBH 86.4 / AIME 24 71.9 / GPQA-Diamond 65.5 | ✅ | Exact match to the Psyche column of the official benchmark table |
| M7 | RefusalBench 74.6% vs 59.5% for Hermes 4 70B; "answered 74.6% of questions that other aligned models refuse" | ✅ with nuance | Both numbers exact. Nuance: 74.6% is the **non-reasoning** 4.3 variant (reasoning is 72.29%), and 59.5% is the **70B reasoning** variant (non-reasoning 70B is 49.07%) — the brief compares across modes |
| M8 | "On raw frontier benchmarks Claude Opus still leads" | ✅ | As of Sept 2026, Claude Opus 5.5 tops the Artificial Analysis Intelligence Index (~57.6), with GPT-5.6 Sol reported marginally higher in some compilations. The point stands; the model generation is 2025-era in the brief |
| M9 | **"Qwen3-Coder 32B Instruct" Q4_K_M, ~55 tok/s @32K, 71.4% SWE-bench Verified, beats GPT-4o-mini on HumanEval+/SWE-bench Verified** | ❌ | **No such model exists.** The official Qwen3-Coder family is 480B-A35B, **30B-A3B**, and Qwen3-Coder-Next (80B-A3B); Qwen's own docs explicitly list 14B/8B/7B/**32B**/4B as *not* official sizes (verified July 2026), and the "Qwen3-Coder-32B" the brief cites appears only in low-quality community blogs. The real 30B-A3B (30.5B total / 3.3B active, 48 layers, 32 Q-heads / **4 KV heads**, 262K ctx) scores **50.3%** SWE-bench Verified (OpenHands; Nebius) / 51.6% Qwen-reported — not 71.4%. That 71.4% figure matches DeepSeek V4 Pro, and the "32B" is likely confused with Qwen2.5-Coder-32B (a different, 128K-context dense family) |
| M10 | Gemma 4 26B-A4B — Q4_K_M, MoE, ~16 GB, ~85 tok/s, 256K context, "best overall" | ⚠️ | Model is real (Apr 2026, Apache 2.0, 25.2B total / 3.8B active, 262K ctx, native function calling). ~16 GB is right (measured GGUF 15.64 GiB; 17.5 GiB VRAM at 32K). But **~85 tok/s is a bandwidth *estimate* from a hardware-guidance site**; measured reports on a 4090 are 149–194 tok/s (one report: 192K context allocated inside 20.9 GB). The number is directionally conservative but wrongly attributed |
| M11 | Qwen 3.6 27B = best dense reasoning model | ✅ | Real (Apr 22, 2026; 262K ctx, vision, Apache 2.0; Q4_K_M ≈ 16.8 GB; measured ~43 tok/s on a 4090 in a community run). Qwen claims it beats the previous-gen 397B-A17B flagship on SWE-bench Verified (77.2% vs 76.2%) — vendor-sourced but consistent across write-ups |
| M12 | gpt-oss 20B "praised for the cleanest tool calls", ~14 GB, lots of headroom | ⚠️ | Model qualifies and fits with the most headroom of anything listed (~12–14 GB MXFP4, 131K ctx). But "cleanest tool calls" is sentiment, not a benchmark: τ-bench Retail 54.8% vs 67.8% for gpt-oss-120B. It is a good *cheap* tool-caller, not the best one |
| M13 | llama.cpp for solo use, vLLM or TensorRT-LLM for concurrency; "Ollama is fine but loses 10–15% throughput" | ⚠️ | Hermes's own docs name vLLM/SGLang for production serving (never TensorRT-LLM) and ship a *managed llama.cpp runtime* for local use; Ollama's measured overhead was 10.3% on an RTX 5060 Ti and 14% on an M3 Max in one 2026 test, but 2–8% in several others — "10–15%" is the pessimistic tail, not the central estimate |
| M14 | **Llama 3.3 70B IQ2_XXS (2.4 bpw) fits in 23.1 GB and delivers ~14 tok/s — "usable"** under the 64K floor | ❌ | Fails twice over. (a) Arithmetic: Llama-3.3-70B has 80 layers × 8 KV heads × 128 head_dim, so its KV cache costs **320 KiB/token** — **20 GiB at 64K** alone. ~21–23 GB of weights + 20 GiB of cache does not fit a 24 GB card, at any speed. (b) Policy: Hermes's managed local runtime "never offers builds smaller than 4-bit… a machine that can't run the 4-bit build simply can't run that model", and the 70B's 4-bit build is ~40 GB. Drop the 70B line entirely |
| M15 | Custom endpoint config; `provider: custom` is first-class, not an alias; `/model custom` auto-detects a single loaded model; works with Ollama, vLLM, llama.cpp server, SGLang, LocalAI | ✅ | Verbatim from the providers doc and FAQ |
| M16 | Embedding/session-search sidecar via `auxiliary: session_search` pointing at a local embedding endpoint | ⚠️ | The exact config block is documented by the Hugging Face "Local Agents with llama.cpp" guide for Hermes. But it is version-sensitive: a Sept-2026 practitioner reference reports the auxiliary `session_search` LLM slot no longer exists in current builds (session search returns DB content directly via SQLite FTS5) and that semantic recall now flows through **memory-provider plugins** (LanceDB, Honcho, Mem0, …) that accept any OpenAI-compatible embedding endpoint. Verify against your installed version before wiring it |
| M17 | Hermes 4 405B on OpenRouter: $1/$3 per M tokens, 131,072 context, "few-dollars" daily Deep Research | ✅ (facts) | OpenRouter confirms $1/$3, 131K, served by Nebius Token Factory, ~33 tok/s P50. A heavy run (~500K in / 100K out) ≈ $0.80 — the cost estimate is fair. The *capability* assumption behind it is the weak link → see §3.4 |
| M18 | Start local-only; add the cloud planner only when quality plateaus | advisory | Not a factual claim, but worth flagging that it sequences the *hardest* part (top-level multi-hop planning/synthesis) last, which is where a 24 GB local model is most likely to disappoint |

---

## 3. The corrections that actually change the plan

### 3.1 The recommended local model does not exist

"Qwen3-Coder 32B Instruct" is not an official Qwen release, and the 71.4% SWE-bench Verified figure
attached to it belongs to a different model (it tracks DeepSeek V4 Pro's reported score; Qwen3-Coder-Next
lands at ~70.6–71.3%). Real, checkable Qwen3-Coder options:

| Model | Architecture | Context | SWE-bench Verified | Local feasibility (24 GB) |
| --- | --- | --- | --- | --- |
| Qwen3-Coder-480B-A35B | 480B MoE / 35B active | 256K | 69.6% (Qwen) | ❌ data-centre only |
| Qwen3-Coder-30B-A3B | 30.5B MoE / 3.3B active | 262K | 50.3–51.6% | ✅ Q4_K_M ≈ 18.6 GB; 6 GiB KV at 64K |
| Qwen3-Coder-Next | 80B MoE / 3B active (hybrid attn) | 256K | ~70.6–71.3% | ⚠️ Q4_K_M ≈ 48.7 GB → needs 2×24 GB or offload |
| Qwen2.5-Coder-32B (if that's what was meant) | 32B dense | 128K | ~62.5% (community) | ✅ ~19 GB, but a 2024-generation model |

The brief's advice is otherwise sound: use a **30B-class MoE with ~3B active parameters** for tool-calling
work on a 24 GB card — it is fast, fits, and clears 64K. The name and the score were the problem.

### 3.2 The KV cache, not the weights, is what the 64K floor really costs you

The brief treats 64K context as a soft tax on VRAM headroom. It is the dominant term. For a standard
grouped-query attention model:

```
KV bytes/token = 2 (K+V) × layers × kv_heads × head_dim × bytes_per_element   [2 B at fp16]
```

| Model | Layers × KV heads × head_dim | KV per token (fp16) | KV at 64K |
| --- | --- | --- | --- |
| Hermes 4.3 36B (Seed-OSS-36B base) | 64 × 8 × 128 | 256 KiB | **16 GiB** |
| Llama 3.3 70B | 80 × 8 × 128 | 320 KiB | **20 GiB** |
| Qwen3-Coder-30B-A3B | 48 × 4 × 128 | 96 KiB | 6 GiB |
| Gemma 4 26B-A4B / Qwen3.6-27B | hybrid / sliding-window attention | — | ~1–2 GiB (measured: 262K ctx with q4_0 KV ≈ 23/24 GB for Qwen3.6-27B) |

(Seed-OSS-36B figures read directly from `ByteDance-Seed/Seed-OSS-36B-Base`'s `config.json`:
`num_hidden_layers: 64`, `num_key_value_heads: 8`, `head_dim: 128`, `max_position_embeddings: 524288`.)

This single table explains three of the brief's four errors: the 36B is not a one-card model at 64K, the
IQ2 70B is not a one-card model at all, and the models that *do* work cleanly on a 4090 at 64K are either
small-active MoEs or 2026 hybrid-attention designs.

### 3.3 The Hermes 4.3 36B verdict is right — and worth keeping in the brief

The conclusion "does not comfortably fit your single 24 GB card at good quality" is correct, the benchmark
set is copied accurately, and the two-GPU / A100-80GB statements hold. Just say *why*: 21.8 GB of Q4
weights plus a 16 GiB KV cache at the mandatory 64K window (37.8 GB total). And note the corollary the brief
misses: because Hermes's managed runtime refuses sub-4-bit builds, you cannot lawfully "fit" this model on
one card through the supported path — that is a supported/unsupported distinction, not a speed trade-off.

### 3.4 The weakest link: Hermes 4 405B as the "planner brain"

This is the recommendation I'd reverse. Hermes 4 405B is an August 2025 fine-tune of Llama-3.1-405B. On the
Artificial Analysis panels OpenRouter surfaces for it, its *agentic* profile is poor by 2026 standards:

| Benchmark (Hermes 4 405B, reasoning) | Score |
| --- | --- |
| Terminal-Bench Hard (agentic coding / terminal) | 11.4% |
| τ²-Bench Telecom (dual-control tool use) | 22.2% |
| AA-LCR (long-context reasoning) | 22.3% |
| HLE | 10.9% |
| AA-Omniscience non-hallucination rate | 5.5% |

For a workload whose stated real benchmark is "can the model read a file, call the terminal, preserve the
requested format, recover from a failed tool, and complete a second turn without drifting", those are the
wrong numbers — and the long-context reasoning score is the one that matters most for cross-source
synthesis. Meanwhile, as of Sept 2026 the frontier is Claude Opus 5.5 / GPT-5.6-class (~57–59 AA Intelligence
Index), and open-weight leaders like DeepSeek V4 Pro / GLM-5.3 / Kimi K3 score at or above 44–53, far above
what a 405B Llama-3.1 fine-tune delivers. The OpenRouter page's own traffic data reinforces this: the top
apps sending tokens to Hermes 4 405B are roleplay front-ends, not agent harnesses.

Keep the *architecture* of the recommendation (offload top-level planning and synthesis to a cloud model);
change the *model*. If you specifically want the Hermes lineage, route Hermes 4.3 36B (or Portal-routed
models) for short-context work and use a current tool-calling frontier/adjacent model as the planner. Also
worth noting: the brief promises "few-dollars daily" runs, which is fair at $1/$3, but that pricing is not
special in 2026 — the same money buys much stronger agentic models.

### 3.5 Framework details that matter for a research loop (not in the brief)

- **Web results are budgeted, not summarised.** `web_extract` truncates deterministically at 15,000
  characters by default (`web.extract_char_limit`, max 500,000) and writes the full text to disk with a
  footer telling the agent how to page through it. Long-form research needs that limit raised or an
  `execute_code` stage, or the agent will work from head/tail excerpts.
- **Duplicate searches are coalesced and cached** — identical concurrent queries from a subagent fan-out
  collapse into one backend request, and extracted URLs are cached under `~/.hermes/cache/web/` across CLI,
  gateway, cron and subagent processes. Good for cost, but it means "N independent subagents" are less
  independent than they look.
- **The keyless ring is a rescue path, not a plan.** It is explicitly last-resort, rate-limited under burst
  load, and even keyed/managed backends do a one-shot non-sticky rescue to it on failure. For a daily
  research job, budget a keyed provider (Firecrawl 500 credits/mo free tier, or self-hosted SearXNG for
  search + a keyed extractor, since SearXNG cannot extract).
- **Deep research has no single switch.** The docs expose delegation, `execute_code`, cron, memory, MCP and
  document reading as separate features; "Deep Research" as a named product appears in third-party content,
  not the official docs.

### 3.6 The embedding sidecar is the right idea with a version risk

Keeping memory search local while the planner is cloud is sound, and there is an official-adjacent config
for it (the HF llama.cpp agents guide shows `auxiliary.session_search.base_url`). But current Hermes builds
appear to have moved on: session search now returns SQLite FTS5 results directly, and semantic recall is
handled by pluggable memory providers whose embedding endpoint you configure. Plan for the *memory
provider* path (e.g. LanceDB/Honcho with a local OpenAI-compatible embedding endpoint such as
`nomic-embed-text` or `EmbeddingGemma-300M`) and treat the `auxiliary.session_search` block as a
check-your-version detail.

---

## 4. Corrected local shortlist for one RTX 4090 (24 GB) under Hermes's 64K floor

| Model | Type | Q4 weights | Context | Fits 64K on one 4090? | Notes |
| --- | --- | --- | --- | --- | --- |
| **Gemma 4 26B-A4B** | MoE, ~3.8B active | 15.6 GiB | 256K | ✅ ~17.5 GiB VRAM at 32K; 192K consumed within 20.9 GB in a measured run | Measured 149–194 tok/s; native function calling; Apache 2.0; best speed/headroom balance |
| **Qwen3.6-27B** | dense 27B, hybrid attn | 16.8 GB | 262K | ✅ measured 262K + q4_0 KV ≈ 23/24 GB | ~43 tok/s on a 4090; strongest coding/agentic claim of the local options (vendor: SWE-bench Verified 77.2%) |
| **Qwen3-Coder-30B-A3B** | MoE, 3.3B active | ~18.6 GB | 262K | ⚠️ tight — 6 GiB fp16 KV at 64K (use q8_0 KV) | Purpose-built tool-call format; 50.3–51.6% SWE-bench Verified |
| **gpt-oss-20B** | MoE, ~3.6B active | ~12–14 GB | 131K | ✅ most headroom | τ-bench Retail 54.8%; leaves room for an embedding sidecar |
| Hermes 4.3 36B | dense 36B | 21.8 GB | 512K | ❌ 21.8 GB + 16 GiB KV = ~37.8 GB | 2×24 GB or bust; Q8_0 on an 80 GB card |
| Llama 3.3 70B (any quant) | dense 70B | ~40 GB at 4-bit | 128K | ❌ | Sub-4-bit builds are below Hermes's supported quality floor; 4-bit needs ~40 GB |

**Two practical notes.** First, Hermes's own managed local runtime already enforces most of this for you:
it prices every catalog model against your GPU *including* context/KV state, picks the highest-quality ≥4-bit
build that fits fully in VRAM, guarantees ≥64K, and grows the window as needed (spilling expert weights —
never the attention cache — to RAM if it must). Using it avoids most foot-guns. Second, if you drive
llama.cpp/vLLM yourself, set the context explicitly (`--ctx-size 65536`) and remember Hermes's own warning
for Ollama: its `/api/show` reports the model's *maximum* context, not the effective `num_ctx`, so set
`OLLAMA_CONTEXT_LENGTH=64000` (or the equivalent) and match it in `config.yaml`.

## 5. Corrected recommended stack

1. **Local tier** — **Gemma 4 26B-A4B Q4_K_M** if throughput and headroom matter most (measured ~150–190
   tok/s, huge context ceiling, native tools); **Qwen3.6-27B Q4_K_M** if you want the strongest local
   coding/agentic quality and can live with ~43 tok/s. Both fit a 24 GB card with a real 64K window.
   Second choice for tool-call-heavy coding: Qwen3-Coder-30B-A3B with a quantised KV cache.
2. **Planner/synthesis tier** — a current (2026) frontier or frontier-adjacent model with verified tool
   calling, not Hermes 4 405B. If staying in the Hermes lineage matters, use Hermes 4.3 36B (short context)
   or Portal-routed models; keep a low-refusal model available as a *policy* escape hatch, not as the
   reasoning engine. Verify that your chosen gateway route actually accepts `tools` before committing the
   workflow to it.
3. **Web search** — keyed Firecrawl (500 credits/mo free) or self-hosted SearXNG for search plus a keyed
   extractor (SearXNG is search-only); keep the keyless ring as automatic failover, and remember xAI search
   results are model-generated, so don't cite them blind. If you hold a paid Nous Portal subscription,
   `hermes setup --portal` is the lowest-friction path.
4. **Memory** — configure a memory provider with a local OpenAI-compatible embedding endpoint; treat
   `auxiliary.session_search` as version-dependent.
5. **Engine** — Hermes's managed llama.cpp runtime for simplicity; llama.cpp server for control; vLLM/SGLang
   only if you start serving concurrent requests (Hermes docs' own recommendation).
6. **Sequencing** — start local, but validate the *planner* path early with real multi-hop research tasks;
   the local model is the part of this stack least likely to be the bottleneck.

---

## 6. Residual uncertainty

- **Hermes catalog specifics change fast.** Whether the managed runtime currently certifies
  Gemma 4 26B-A4B / Qwen3.6-27B at ≥64K *on your exact card + driver* should be checked in
  Settings → Providers → Local Models on your install; the docs describe the policy, not the row list.
- **Throughput numbers are community-sourced** and vary up to ~2× with context length, quantisation, KV
  quantisation and runtime build. The 4090 figures here are reports, not my measurements.
- **One docs contradiction inside Hermes itself:** the Features Overview says "3 concurrent subagents by
  default" while the Delegation guide says 10. Check `delegation.max_concurrent_children` on your build.
- **One OpenRouter contradiction:** the Hermes 4 405B model page's description says it supports function
  calling and tool use; a FAQ fragment on the same page says it does not accept tools. Confirm with a live
  request before depending on it either way.
- **Frontier rankings above come from leaderboard compilations** (benchlm / modelgrep / Artifical Analysis
  changelog) and shift weekly; treat the *rank ordering* as soft, the *generation gap* as hard.
- **Minor date discrepancy:** the Hermes 4.3 GGUF repo shows commit dates ~10 months before Sept 2026
  (≈Nov 2025) while the Nous blog says December 2025; the blog is treated as authoritative here.

---

## 7. Sources

**Hermes Agent (official):** docs index `docs/llms.txt`; Web Search & Extract; Local Models; Quickstart;
Providers/Integrations; FAQ; Features Overview; Code Execution; Subagent Delegation; Delegation & Parallel
Work; Cron; Memory / Memory Providers; Skills Hub (`optional-skills/research/searxng-search`).
`hermes-agent.nousresearch.com/docs/...`

**Nous Research models:** "Introducing Hermes 4.3" blog (December 2025, Psyche, 144k tok/s, 24 nodes);
HF card `NousResearch/Hermes-4.3-36B` (benchmark table, RefusalBench table); HF GGUF repo file sizes
(Q3_K_M 17.6 GB, **Q4_K_M 21.8 GB**, Q5_K_M 25.6 GB, Q8_0 38.4 GB, BF16 72.3 GB); HF OpenRouter page for
Hermes 4 405B ($1/$3, 131K, Nebius, AA benchmark panel); Hermes 4 family reporting (14B/70B/405B,
Aug 2025); upstream issue NousResearch/hermes-agent#53347 (64K hard failure).

**Architectures / arithmetic:** `ByteDance-Seed/Seed-OSS-36B-Base` `config.json` (64 layers, 8 KV heads,
head_dim 128, 512K max positions); Llama-3.1/3.3-70B GQA configuration (80 layers, 8 KV heads, 128).

**Qwen:** Qwen3-Coder blog (July 22, 2025; 480B-A35B, 256K→1M); HF card
`Qwen/Qwen3-Coder-30B-A3B-Instruct` (30.5B/3.3B, 48 layers, 32 Q-heads / 4 KV-heads, 262,144 ctx);
QwenLM/Qwen3-Coder GitHub (official family list incl. Qwen3-Coder-Next); third-party check that
7B/8B/14B/**32B**/4B are not official sizes; Nebius OpenHands writeup (30B-A3B = 50.3% SWE-bench Verified).

**Other local models:** Gemma 4 26B-A4B launch coverage and OpenRouter listing (Apr 2–3, 2026; 25.2B/3.8B
active; 262,144 ctx; Apache 2.0; native function calling); measured RTX 4090 GGUF benchmarks
(15.64 GiB file, 17,572 MiB @32K, 149–194 tok/s, 192K in 20.9 GB); Qwen3.6-27B hardware guide + 4090
community run (~43 tok/s at Q4_K_M; 262K with q4_0 KV ≈ 23/24 GB); gpt-oss-20B τ-bench Retail 54.8% /
Airline 38.0%; Ollama-vs-llama.cpp overhead tests (10.3% / 14% vs 2–8% ranges).

**Third-party Hermes ecosystem:** Hugging Face "Local Agents with llama.cpp" (Hermes custom-endpoint config
and `auxiliary.session_search` block); `notebooklm-mcp-cli` setup guides; Practitioner's Reference (Sept 2026)
on session search / removed auxiliary slots; LanceDB semantic-memory plugin writeup.

**Leaderboards (accessed 2026-09-26):** Artificial Analysis changelog; benchlm and modelgrep Sept-2026
Intelligence Index compilations; OpenRouter model pages for pricing/latency.
