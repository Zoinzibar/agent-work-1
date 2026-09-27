# Updated workflow: native Web Search & Deep Research on Hermes Agent
## Arch Linux / single RTX 4090 (24 GB) — corrected edition

> **Lineage:** this is the workflow proposed in
> [`initial-agent-research.md`](initial-agent-research.md), rewritten with every correction from
> [`claim-verification-analysis.md`](claim-verification-analysis.md) applied. **This file is safe to act
> on; the initial brief is not.** Each section cites the graded claims (`F1`–`F16`, `M1`–`M18`) and
> findings (analysis §3–§7) it depends on, so every step can be traced back to a verified source.

> ## ⏳ Freshness line — read this before acting
> Claims verified **2026-09-26**. The *framework and VRAM-arithmetic* parts of this guide (§1, §2, §4.1,
> §4.3) are durable. The *specific model picks* (§4.2, §5) assume a ~6-week half-life — the local tier
> already moved once during verification (Qwen3.8-27B superseded Qwen3.6-27B on 2026-08-14). **Re-check
> §4.2, §5 and §7 before downloading or subscribing to anything.**

---

## 0. TL;DR — what changed at a glance

The brief's **architecture** was right and survives verification: run web search and the cheap,
high-frequency parts of research loops locally, and offload multi-hop planning/synthesis to a bursty
cloud model. Its **model picks** are where the errors were, and all three load-bearing ones are replaced
here:

| Layer | Initial brief said | This workflow says |
| --- | --- | --- |
| Local model (extraction, tool calls, subagent legs) | "Qwen3-Coder 32B Q4_K_M" †2 | **❌ does not exist** (analysis M9) → **Qwen3.8-27B Q4_K_M**; Gemma 4 26B-A4B when throughput matters most |
| "Bigger" local fallback | Llama 3.3 70B IQ2_XXS †3 | **❌ removed entirely** — 20 GiB of KV cache at the mandatory 64K window plus ~21–23 GB of weights cannot fit in 24 GB of VRAM **fully on-GPU**, at any quantisation (M14). RAM spill can technically run it, slowly (§4.4), but there is no *usable* 70B-class path on one 24 GB card |
| Cloud "planner brain" | Hermes 4 405B via OpenRouter †5 | **❌ weak agentic panel** (§3.4) → a **current (2026) frontier/frontier-adjacent model with verified tool calling** |
| Zero-setup web search | Keyless ring as the default plan | **⚠️ repositioned** — the ring is a documented last-resort rescue path; run a keyed provider (or self-hosted SearXNG + keyed extractor) and let the ring be automatic failover (F5, §4) |
| "Parallel/xAI routing" †1 | One backend routing via Grok | **❌ conflation** — Parallel and xAI are separate; xAI results are LLM-generated, so never cite them blind (F8) |
| Embedding sidecar config | `auxiliary: session_search` block | **⚠️ version-sensitive** — plan for memory-provider plugins + a local embedding endpoint; verify the auxiliary slot on your build (M16) |
| Sequencing | Start local-only; add the planner when quality plateaus | **⚠️ inverted priority** — validate the planner path *early*, it's the most likely failure point (M18, §6) |

---

## 1. What you're actually configuring

*Verified as stated — no changes from the brief.*

- **Hermes Agent** is Nous Research's open-source agent framework. It runs in the terminal, a native
  desktop app, messaging platforms, and IDEs (via ACP), in the same category as Claude Code / Codex /
  OpenClaw. [F1 ✅]
- It works with **any LLM provider** — Nous Portal, OpenRouter, OpenAI, Anthropic, Google, or any
  OpenAI-compatible endpoint — including local models via managed llama.cpp, Ollama, vLLM, SGLang,
  LocalAI. [F2 ✅]
- **The hard constraint: 64,000 tokens of context, minimum.** Models below the floor are **rejected at
  startup** — a hard failure, not a warning (upstream issue #53347). This single requirement drives all
  the VRAM arithmetic in §4. [F3 ✅]
- **No lock-in:** switch providers at any time with `hermes model`. [M15 ✅]

---

## 2. Workflow 1 — native Web Search

Web search ships **built in** — no custom skill needed. [F4 ✅]

### 2.1 Setup (two commands cover every path)

```bash
hermes tools            # → Web Search & Extract → pick a provider; the wizard stores the key/URL
hermes setup --portal   # paid Nous Portal path: Tool Gateway enables all gateway tools, no per-tool keys
```

[F4 ✅, F6 ✅ — both verified nearly word-for-word against the official docs]

### 2.2 Provider ladder (corrected ordering)

1. **Run one keyed provider as your primary.** The free tier of Firecrawl (500 credits/month) is the
   cheapest keyed entry; or self-host **SearXNG for search** — but note SearXNG is *search-only* and
   cannot extract pages, so pair it with a keyed extractor. [§4 new findings]
2. **The keyless ring is your automatic failover, not your plan.** With no credentials, requests rotate
   across Exa → Parallel → Firecrawl → Keenable free tiers, multi-hop "until one serves or all are
   throttled." This is verified — but repositioned: the docs call it **last-resort**, it is
   vendor-rate-limited under burst load, and even keyed/managed backends fall back to it with a one-shot,
   non-sticky rescue. Great safety net; bad primary. [F5 ✅ + §4]
3. **xAI is a separate, opt-in backend — do not conflate it with Parallel.** [F8 ❌, the brief's third
   error, corrected]
   - **Parallel** is its own index-backed search/extract provider and a keyless-ring member.
   - **xAI (Grok)** is *search-only*, requires an explicit `web.backend: "xai"` (deliberately **not** in
     the auto-detect chain), and — per the docs' own trust-model caveat — returns **LLM-generated**
     titles, descriptions and URL choices rather than index-backed results. In a citation-driven
     research loop that is an integrity risk: **never cite xAI results blind.**
4. **SearXNG is now a first-class built-in backend** — `web.search_backend: "searxng"` in config. The
   skill (`hermes skills install official/research/searxng-search`) is only an optional curl-direct
   fallback. And drop the "air-gapped" framing: a self-hosted SearXNG still queries live search engines.
   [F9 ⚠️]
5. Exa remains a good keyed pick for research legs: "neural search with semantic understanding, good for
   research and finding conceptually related content" (docs verbatim). [F7 ✅]

### 2.3 Operational behaviour to design around [§4 new findings]

- **Extraction is budgeted, not summarised.** `web_extract` truncates deterministically at **15,000
  characters** by default (`web.extract_char_limit`, clamped 2,000–500,000) and writes the full page to
  disk with a footer telling the agent how to page through it. For long-form research either raise the
  limit or add an `execute_code` stage — otherwise the agent works from head/tail excerpts.
- **Duplicate queries are coalesced and pages are cached.** Identical concurrent queries from a subagent
  fan-out collapse into one backend request; extracted URLs are cached under `~/.hermes/cache/web/`
  across CLI, gateway, cron and subagent processes. Great for cost — but "10 independent subagents" are
  less independent than they look.

---

## 3. Workflow 2 — Deep Research: you compose it (there is no switch)

**Correction [F10 ⚠️]:** the docs have **no named "Deep Research" mode or product**. What exists is a
composable capability set — plus a community `deep-research` skill on the Skills Hub. Assemble it from:

- **Delegation** — `delegate_task` spawns isolated subagents for parallel research workstreams; only the
  final summary returns to the parent's context. The docs contradict themselves on default fan-out
  (Features Overview says 3, the Delegation guide says 10) — check `delegation.max_concurrent_children`
  on your build. [F11 ✅ + §7]
- **`execute_code` (Programmatic Tool Calling)** — collapses multi-step pipelines into single inference
  calls; intermediate tool results never enter the context window, only `print()` output does (timeout
  and stdout caps apply). [F12 ✅]
- **Your own documents** — native document reading/context files. **NotebookLM via MCP is third-party**:
  the `notebooklm-mcp-cli` server drives NotebookLM through *browser automation*, and the community
  guides themselves recommend keeping a non-NotebookLM fallback. Treat it as a bolt-on, not a Hermes
  capability. [F13 ⚠️]
- **Cron** — natural-language recurring jobs ("daily digest" research on autopilot). Two caveats the
  brief omitted: scheduled output is delivered to **messaging platforms**, and **every run bills the full
  model cost**. [F14 ✅]
- **MCP** — connect any MCP server to bolt on arXiv, SEC filings, internal wikis as research sources.
  [F15 ✅]
- **Token budget reality** — Deep Research is far hungrier than a single search: multi-turn planning, one
  subagent context per workstream, long synthesis. The claim is directionally certain but unquantified;
  one independent data point: Artificial Analysis measured Qwen3.8-27B emitting **160M output tokens**
  across its agentic index testing vs a 43M median for comparable open-weight models. This asymmetry is
  what justifies the local/cloud split in §5. [F16 ⚠️]

---

## 4. Model choice for one RTX 4090 (24 GB) — corrected

### 4.1 The arithmetic that drives everything [§3.2, verified]

The brief treated 64K context as a soft tax on VRAM headroom. More precisely, the KV cache is **the
term that invalidates the larger-model fallback tier**: for the 36B and 70B options it exceeds what can
fit alongside the weights on one 24 GB card at any usable speed. It is *not* dominant for every model —
for the recommended Qwen3.8-27B, ~4 GiB of KV sits against ~17–17.8 GB of weights; that small cache
(hybrid attention, 16 full-attention layers) is exactly why it fits where the larger models do not:

```
KV bytes/token = 2 (K+V) × layers × kv_heads × head_dim × bytes_per_element   [2 B at fp16]
```

| Model | Geometry | KV per token (fp16) | KV at 64K | Basis |
| --- | --- | --- | --- | --- |
| Hermes 4.3 36B (Seed-OSS-36B base) | 64 layers × 8 KV × 128 | 256 KiB | **16 GiB** | computed |
| Llama 3.3 70B | 80 layers × 8 KV × 128 | 320 KiB | **20 GiB** | computed |
| Qwen3-Coder-30B-A3B | 48 layers × 4 KV × 128 | 96 KiB | 6 GiB | computed |
| Qwen3.8-27B | 16 full-attn layers × 4 KV × 256 | 64 KiB | ~4 GiB (≈2.3 GB/32K, measured) | computed + measured |

### 4.2 The corrected shortlist [analysis §5 — recommendations, refreshed 2026-09-26, and they decay]

| Model | Released | Q4 weights | Fits 64K on one 4090? | Role in this workflow |
| --- | --- | --- | --- | --- |
| **Qwen3.8-27B** ⭐ | 2026-08-14 | ~17–17.8 GB | ✅ ~22–23 GB all-in (17.8 GB + ~4.6 GB f16 KV) | **Default local pick.** Dense 27B VLM (hybrid attn), Apache 2.0, 262K native. AA Intelligence Index **52 vs 38** for the superseded Qwen3.6-27B at identical size. ~50 tok/s decode plain, ~40 at 128K depth. *Caveat: defaults to xhigh reasoning effort and over-thinks — budget tokens.* |
| Gemma 4 26B-A4B | 2026-04 | 15.6 GiB | ✅ ~17.5 GiB at 32K; 192K measured within 20.9 GB | **Throughput pick.** MoE ~3.8B active, *measured* 149–194 tok/s on a 4090 — the brief's "~85 tok/s" was a wrongly-attributed bandwidth estimate [M10 ⚠️]. Native function calling. |
| Qwen3-Coder-30B-A3B | 2025-07 | ~18.6 GB | ⚠️ tight — 6 GiB fp16 KV at 64K (use q8_0 KV) | Only if you specifically want its purpose-built tool-call format. Real SWE-bench Verified is **50.3–51.6%** (OpenHands/Qwen) — not the brief's 71.4%, which tracks DeepSeek V4 Pro [M9 ❌]. Now an older generation. |
| gpt-oss-20B | 2025-08 | ~12–14 GB | ✅ most headroom | Headroom pick — leaves room for an embedding sidecar. τ-bench Retail 54.8%. "Cleanest tool calls" was sentiment, not a benchmark, and the model is 13 months old [M12 ⚠️]. |
| ~~Qwen3.6-27B~~ | 2026-04-22 | 16.8 GB | ✅ | **Superseded by Qwen3.8-27B** — same size, licence and VRAM; it was the analysis's own pick until it proved six weeks stale [M11 ⚠️]. |

### 4.3 Explicitly ruled out

- **"Qwen3-Coder 32B Instruct"** — the brief's headline pick, and it **does not exist**. The official
  Qwen3-Coder family is 480B-A35B, 30B-A3B and Qwen3-Coder-Next (80B-A3B); Qwen's own materials list 32B
  among the *non*-official sizes. [M9 ❌] The brief's underlying instinct — a 30B-class MoE with ~3B
  active parameters on a 24 GB card — was sound; the name and the score were the problem. Likewise, a
  rumoured "Qwen3-Coder-Next 30B Flash" at ~18 GB is **unconfirmed by any primary source — do not plan
  around it.** [§3.1]
- **Llama 3.3 70B as an on-GPU path, at any weight quantisation** — 20 GiB of KV cache at the mandatory
  64K window (the attention cache is the one thing the runtime never spills) plus ~21–23 GB of weights
  cannot fit in 24 GB of VRAM. Scope note: this is a *fully on-GPU / practical-performance at 64K*
  verdict. The managed runtime **does** support spilling overflow weights to system RAM (§4.4), so a
  single-4090 *host* can technically run it — with most weights in RAM, at RAM-bound speed. That is a
  crawl, not a usable fallback, so the IQ2_XXS recommendation stays deleted rather than amended. [M14 ❌]
- **Hermes 4.3 36B on one card** — its benchmark numbers are real (MATH-500 93.8, MMLU 87.7, BBH 86.4,
  AIME 24 71.9, GPQA-Diamond 65.5 [M6 ✅]) and the brief's "does not fit a single 4090 at good quality"
  verdict was **correct**: 21.8 GB Q4_K_M weights + 16 GiB KV at 64K ≈ **~39 GB**. It needs 2×24 GB or an
  80 GB card (Q8_0 = 38.4 GB fits an A100 with KV). *On-GPU at 64K*, that is: Q3_K_M plus a heavily
  quantised KV cache lands ~22 GB on one card (technically loadable, quality-degraded, zero headroom),
  and RAM spill would merely run it slowly — neither changes the recommendation. [M4/M5 ✅] Two framing
  fixes: "nearly matches the 70B at half the VRAM" breaks *precisely at the 64K window you need* [M3 ⚠️],
  and the RefusalBench headline mixed modes — like-for-like it is **74.60 (non-reasoning 4.3) vs 49.07
  (non-reasoning 70B)**, not 74.6 vs 59.5 [M7 ⚠️]. Keep a Hermes model available as a low-refusal
  *policy escape hatch* for sensitive research topics — not as the reasoning engine.
- **Hermes 4 405B as the planner** — see §5, step 2.
- **"Claude Opus leads on raw frontier benchmarks"** → softened to "at or near the frontier"; the
  ordering is index- and effort-dependent and shifts weekly. Treat the *generation gap* as hard, the
  *rank order* as soft. [M8 ⚠️]

### 4.4 Serving engine [M13 ⚠️ + §5 practical notes]

- **Managed llama.cpp runtime** (simplest; Hermes's default): it prices every catalog model against your
  GPU *including* context/KV state, picks the highest-quality ≥4-bit build that fits, guarantees ≥64K,
  grows the window as needed, and **spills overflow to system RAM** (expert weights first, never the
  attention cache). RAM spill is a supported-but-slow path, not a refusal — this corrects both the brief
  and the v1 analysis. [§3.3]
- **llama.cpp server** (control): set the context explicitly — `--ctx-size 65536`.
- **vLLM/SGLang** for concurrent serving (the Hermes docs' own recommendation; they never mention
  TensorRT-LLM). [M13 ⚠️]
- **Ollama** is fine for solo use; measured overhead is ~2–8% in most tests (the brief's "10–15%" is the
  pessimistic tail). **Trap:** Ollama's `/api/show` reports the model's *maximum* context, not the
  effective `num_ctx` — set `OLLAMA_CONTEXT_LENGTH=64000` and match it in `config.yaml`. [§5]
- **Wiring to Hermes** [M15 ✅, unchanged]: if your local server has exactly one model loaded,
  `/model custom` auto-detects it; or set `provider: custom` in `config.yaml` — a first-class provider,
  not an alias, working with Ollama, vLLM, llama.cpp server, SGLang, LocalAI.

---

## 5. Recommended concrete stack — step by step

*Same hybrid architecture as the brief; every specific model and config corrected.*

1. **Local tier (the workhorse)** — **Qwen3.8-27B Q4_K_M** for web-page extraction/summarisation,
   tool-call formatting and simple sub-agent research legs (~22–23 GB all-in at a real 64K window).
   Swap in **Gemma 4 26B-A4B** when raw throughput and parallel subagent fan-out matter more than depth.
   [§6.1]
2. **Planner/synthesis tier (corrected — this is the largest plan change)** — route Deep Research's
   top-level orchestration (multi-turn coherence, long synthesis, citation-quality writing) to a
   **current (2026) frontier or frontier-adjacent model with verified tool calling — not Hermes 4 405B.**
   The 405B is an August-2025 fine-tune whose OpenRouter-mirrored AA panel (reasoning mode, checked
   2026-09-26) reads: Terminal-Bench Hard 11.4%, τ²-Bench Telecom 22.2%, AA-LCR long-context 22.3%,
   HLE 10.9%, non-hallucination rate 5.5% — and its top OpenRouter consumers are roleplay front-ends,
   not agent harnesses. Long-context reasoning is the exact capability cross-source synthesis needs most.
   [§3.4]
   - If the Hermes lineage matters, use **Hermes 4.3 36B for short-context legs** or Portal-routed
     models, and keep a low-refusal model as a policy escape hatch (RefusalBench §4.3) — not as the
     reasoning engine.
   - **Before committing, send one live request to confirm your gateway route actually accepts `tools`**
     — the OpenRouter model page contradicts itself on this. [§7]
   - Cost reality check: the brief's "$1/M in, $3/M out" figure for the 405B was accurate (a heavy
     ~500K-in / 100K-out run ≈ $0.80), but that pricing is no longer special in 2026 — so it is not a
     reason to keep a weak planner. [M17 ✅(facts)]
3. **Web search tier** — keyed Firecrawl (500 free credits/mo) or self-hosted SearXNG + a keyed
   extractor; keyless ring as automatic failover; xAI opt-in only with the citation caveat; paid Portal =
   lowest-friction path. [§2.2]
4. **Memory tier** — use a **memory-provider plugin** (LanceDB, Honcho, Mem0) pointing at a **local
   OpenAI-compatible embedding endpoint** (`nomic-embed-text` or `EmbeddingGemma-300M`) to keep
   memory/session search local even when the main model is cloud. The brief's `auxiliary:
   session_search` config is **version-sensitive** — a Sept-2026 practitioner reference reports the slot
   removed in current builds (session search now returns DB content via SQLite FTS5). Verify against
   your installed version before wiring it. [M16 ⚠️]
5. **Sequencing (inverted from the brief)** [M18 advisory + §6.6] — the brief said "start local-only and
   add the cloud planner when quality plateaus." That defers the step most likely to fail. Instead:
   - **Stand up web search end-to-end locally first** — it genuinely fits a 4090 (§4.2 models handle
     single/few-tool-call lookups fine), and costs nothing to validate.
   - **Validate the planner path early** with real multi-hop research tasks (10+ sources, recovery from a
     failed tool call, format preservation across a second turn — the brief's own operational benchmark).
     The local model is the part of this stack *least* likely to be the bottleneck; multi-hop planning on
     a 24 GB card is where quality plateaus first.

**Bottom line (updated):** hybrid is still the benchmark-justified answer — web search runs fully local;
Deep Research's bursty top-level planning justifies a small cloud spend. What changed is every specific
model attached to that architecture, the search-provider ordering, and the sequencing.

---

## 6. Traceability — what changed, and why

Every deviation from the initial brief maps to a graded claim or verified finding in the analysis:

| Brief passage | Analysis entry | Change applied in this file |
| --- | --- | --- |
| †1 "Parallel/xAI routing … through Grok" | F8 ❌ | Split into two backends; xAI opt-in, search-only, LLM-generated results + don't-cite-blind caveat (§2.2) |
| Keyless ring as zero-setup default | F5 ✅ + §4 | Kept, repositioned as last-resort failover; keyed-provider-first ladder (§2.2) |
| SearXNG as an installable "air-gapped" skill | F9 ⚠️ | First-class built-in backend; skill = optional fallback; search-only; not air-gapped (§2.2) |
| — (not in brief) | §4 | Extract budget (`web.extract_char_limit` 15,000), query coalescing, `~/.hermes/cache/web/` caching (§2.3) |
| "Deep Research is Hermes's multi-step research mode" | F10 ⚠️ | Reframed: no named mode; compose from native features + community skill (§3) |
| NotebookLM as a Hermes capability | F13 ⚠️ | Labelled third-party browser-automation MCP with fallback advice (§3) |
| Default subagent fan-out | F11 ✅ + §7 | Docs 3-vs-10 contradiction flagged; check `delegation.max_concurrent_children` (§3) |
| †2 "Qwen3-Coder 32B Instruct … 71.4% SWE-bench" | M9 ❌ | **Deleted** — model does not exist; real 30B-A3B = 50.3–51.6%; replaced as headline by Qwen3.8-27B (§4.2, §4.3) |
| †3 Llama 3.3 70B IQ2_XXS "usable" fallback | M14 ❌ | **Deleted** — 20 GiB KV + ~21–23 GB weights cannot fit fully on-GPU at 64K, at any weight quantisation; RAM-offload crawl acknowledged but not a usable fallback (§4.1, §4.3) |
| †4 "nearly matches the 70B at half the VRAM" | M3 ⚠️ | Qualified — breaks exactly at the 64K window (§4.3) |
| RefusalBench 74.6% vs 59.5% | M7 ⚠️ | Like-for-like restated: 74.60 vs 49.07 (both non-reasoning) (§4.3) |
| Hermes 4.3 36B fit verdict | M4/M5 ✅ | **Kept and quantified**: ~39 GB at 64K; 2×24 GB or 80 GB card (§4.3) |
| "Claude Opus still leads" | M8 ⚠️ | Softened to "at or near the frontier"; generation gap hard, rank order soft (§4.3) |
| Gemma 4 26B-A4B "~85 tok/s" | M10 ⚠️ | Corrected to measured 149–194 tok/s; kept as throughput pick (§4.2) |
| Qwen 3.6 27B "best dense reasoning" | M11 ⚠️ + §4 | **Superseded by Qwen3.8-27B** (AA 52 vs 38, same footprint) (§4.2) |
| gpt-oss-20B "cleanest tool calls" | M12 ⚠️ | Kept for headroom only; age flagged (13 months) (§4.2) |
| "Ollama loses 10–15%"; TensorRT-LLM | M13 ⚠️ | Central estimate 2–8%; TensorRT-LLM dropped (not in Hermes docs); Ollama `num_ctx` trap added (§4.4) |
| †2/†6 custom-endpoint wiring | M15 ✅ | **Kept verbatim** — `provider: custom`, `/model custom` auto-detect (§4.4) |
| Managed-runtime quantization policy | §3.3 | Corrected: ≥4-bit policy, RAM spill is supported (§4.4) |
| †5 Hermes 4 405B as planner | §3.4 | **Replaced** — weak agentic panel; pick a current frontier/frontier-adjacent tool-calling model; Hermes lineage demoted to escape hatch (§5.2) |
| Embedding sidecar via `auxiliary: session_search` | M16 ⚠️ | Memory-provider plugins + local embedding endpoint; auxiliary slot = check-your-version (§5.4) |
| "Start local-only; add planner when quality plateaus" | M18 + §6.6 | Sequencing inverted: validate the planner path early (§5.5) |

*Not reproduced from the brief:* the 22/7/4-era framing of "August 2026 picks" superlatives ("best
overall", "best dense reasoning model") — subjective, unscored in the analysis, and excluded here by the
same standard.

---

## 7. Re-check before acting (living checklist, from analysis §7)

- [ ] **Local-model freshness** — the tier moves on a ~6-week clock; confirm Qwen3.8-27B is still the
      best 24 GB pick (and whether anything newer has displaced it) before downloading.
- [ ] **Managed-runtime certification** — whether Hermes's catalog certifies Qwen3.8-27B / Gemma 4
      26B-A4B at ≥64K on *your* card + driver: Settings → Providers → Local Models.
- [ ] **Subagent fan-out** — the docs self-contradict (3 vs 10); check `delegation.max_concurrent_children`
      on your build.
- [ ] **Gateway tool support** — send one live request to confirm your cloud route accepts `tools` before
      building the planner tier on it (the OpenRouter page self-contradicts).
- [ ] **Throughput figures** — all 4090 tok/s numbers here are community reports, varying up to ~2× with
      context depth, quantisation and runtime build. Measure on your box.
- [ ] **"Qwen3-Coder-Next 30B Flash"** — still unconfirmed by any primary source as of 2026-09-26;
      revisit only if it appears on the official Qwen3-Coder repo.
- [ ] **`auxiliary.session_search`** — verify the slot still exists on your installed Hermes version
      before wiring the embedding sidecar.

---

*Provenance: derived from `initial-agent-research.md` (the workflow structure and all claims that
verified) and `claim-verification-analysis.md` v2 (every correction, qualification and new finding;
sources with URLs and access dates live there in §8). This file contains no claims that diverge from
those two documents.*
