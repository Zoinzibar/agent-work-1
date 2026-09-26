# Initial agent research (as received)

> ## ⚠️ WARNING — THIS DOCUMENT CONTAINS KNOWN-FALSE MODEL ADVICE
> **Do not act on this brief as written.** It is reproduced unedited as the input to a verification pass.
> **3 of its 33 checkable claims are false and 13 more are materially qualified**
> (see [`claim-verification-analysis.md`](claim-verification-analysis.md)). In particular:
> - †2 — **"Qwen3-Coder 32B Instruct" is not an official model.** No such Qwen release exists, and the
>   71.4% SWE-bench Verified figure attached to it belongs to a different model. The real 30B-A3B scores
>   50.3–51.6%. This is the brief's headline local recommendation: **ignore it.**
> - †3 — **The Llama 3.3 70B IQ2_XXS fallback cannot work.** Its KV cache alone costs 20 GiB at the
>   mandatory 64K window, on top of ~21–23 GB of weights: it does not fit a 24 GB card at any quantisation.
> - †1 — **xAI and Parallel are different providers**, and xAI's results are LLM-generated rather than
>   index-backed — a citation-integrity problem for a research loop.
> - †5 — The Hermes 4 405B planner recommendation rests on poor agentic numbers.
>
> **Markers:** `†N` annotations were inserted for navigation and point to entries in the analysis. They are
> the *only* additions to the body; the text itself is unaltered. **Verified 2026-09-26 — model picks decay
> in weeks; re-check before acting.**

> **Provenance:** This file reproduces the research brief supplied by the user/initial agent, verbatim
> apart from Markdown formatting and decoding of HTML entities (e.g. `&amp;` → `&`), plus the `†` markers
> and the warning above. It is preserved here so the verification in
> [`claim-verification-analysis.md`](claim-verification-analysis.md) can be read against the original text.
> No factual claim in the body has been corrected.

**Brief title (inferred):** Building native Web Search and Deep Research workflows on Hermes Agent (Nous
Research) on an Arch Linux / RTX 4090 (24 GB) box.

---

Here's a full breakdown for building both workflows on Hermes Agent (Nous Research's open-source agent
framework) on your Arch/RTX 4090 box, with model choices tied to actual benchmarks rather than hype.

## 1. What you're actually configuring

Hermes Agent is an open-source AI agent framework by Nous Research that runs in your terminal, a native
desktop app, messaging platforms, and IDEs, in the same category as Claude Code and OpenClaw, and works
with any LLM provider including local models. Critically: Hermes Agent requires a model with at least
64,000 tokens of context — models with smaller windows cannot maintain enough working memory for
multi-step tool-calling workflows and will be rejected at startup. This one constraint drives a lot of
your model decision on a single 24GB card.

## 2. Native Web Search workflow setup

Hermes ships this built-in rather than requiring a custom skill:

- Run the wizard: run `hermes tools`, navigate to Web Search & Extract, and pick a provider — the wizard
  prompts for the required URL or API key and writes it to your config.
- **Zero-setup fallback**: when no credential is present, requests rotate across free-tier vendors (Exa,
  Parallel, Firecrawl, Keenable) so web tools work on a fresh install with zero setup, and a rate-limited
  request fails over to the next vendor automatically.
- **Paid/reliable path**: if you have a paid Nous Portal subscription, web search and extract are available
  through the Tool Gateway with no API key needed — running `hermes setup --portal` logs in and turns on all
  gateway tools at once.
- Provider-specific options worth knowing: Exa does "neural search with semantic understanding, good for
  research and finding conceptually related content", and Parallel/xAI routing routes `web_search` through
  Grok's server-side `web_search` tool, where Grok runs the actual searching and returns top results as
  structured JSON. †1

For local-only/air-gapped setups, there's also a SearXNG skill:
`hermes skills install official/research/searxng-search`.

## 3. Native Deep Research workflow

This isn't a separate product — it's Hermes's multi-step research mode: deep research is multi-step
research where Hermes plans, searches, reads and synthesises across several sources instead of a single
lookup. It composes with a few other native features:

- *Delegates & parallelizes* — spawn isolated subagents for parallel workstreams, useful for fanning out
  research sub-questions concurrently.
- *Programmatic Tool Calling via `execute_code`* collapses multi-step pipelines into single inference calls.
- *Your own documents* — point it at your files and it researches within your own knowledge base, not just
  the open web, and NotebookLM via MCP lets you connect NotebookLM to generate detailed research reports
  from your own sources.
- You can schedule a recurring research task and Hermes runs it on autopilot via built-in cron — good for
  standing "daily digest" research jobs.
- MCP support connects to any MCP server for extended tool capabilities, so you can bolt on arXiv, SEC
  filings, or internal wikis as research sources.

Deep Research is far more token-hungry than a single search (multiple planning turns, multiple tool calls,
long synthesis) — this matters a lot for your local-vs-cloud decision below.

## 4. Model choice for RTX 4090 24GB — what the benchmarks actually say

**If you want the Hermes *model* itself, not just the Hermes *agent framework*:**

The current public family covers four sizes from 14B to 405B parameters, with Hermes 4.3 36B (released
December 2025 on the Psyche distributed training network) the most interesting variant for self-hosters
because it nearly matches the 70B at half the VRAM cost. †4 But: the 36B model fits on a two-GPU RTX 4090
setup at 4-bit quantization or a single A100 80GB at higher precision — it does **not** comfortably fit on
your single 24GB card at good quality. †6 Its actual benchmark numbers are strong though: MATH-500 at 93.8%,
MMLU at 87.7%, BBH at 86.4%, AIME 24 at 71.9%, GPQA Diamond at 65.5%, and notably RefusalBench: Hermes 4.3
scored 74.6% (meaning it answered 74.6% of questions that other aligned models refuse), compared to 59.5%
for Hermes 4 70B — relevant if your research workflow touches sensitive/edgy topics that closed models
over-refuse.

**Honest reality check on frontier gap**: on raw frontier benchmarks Claude Opus still leads — Hermes wins
on different axes: open weights, no per-token cost after you own the GPU, and the ability to run fully
air-gapped. If your agent workload is bounded and you have GPU capacity, Hermes is cheaper and more
controllable.

**Best models that actually fit cleanly in 24GB VRAM for agentic/tool-calling work (2026 benchmarks):**

- Qwen3-Coder 32B Instruct at Q4_K_M is the best model the RTX 4090 can run end-to-end at full quality
  (~55 tok/s at 32K context); †2 it outperforms GPT-4o-mini on HumanEval+ and SWE-bench Verified, with native
  tool-calling that works with the standard OpenAI-compatible endpoint. On agentic coding specifically:
  Qwen3-Coder 32B Q4_K_M scores 71.4% on SWE-Bench Verified and sustains 48–54 tok/s at 32k context. †2
- August 2026 picks include Gemma 4 26B-A4B (Q4_K_M, MoE, ~16GB, ~85 tok/sec, 256K context) as best
  overall, Qwen 3.6 27B as best dense reasoning model, and gpt-oss 20B praised for the cleanest tool calls
  at only ~14GB, leaving huge headroom for context/embedding sidecars.
- Broader framework guidance: llama.cpp for solo use, vLLM or TensorRT-LLM when serving more than one
  concurrent request — Ollama is fine but loses 10–15% throughput.

**What fits vs. Hermes-agent's 64K context floor**: this rules out squeezing a dense 70B in at usable
quality — Llama 3.3 70B Instruct at IQ2_XXS (2.4 bpw) fits in 23.1 GB and delivers ~14 tok/s — usable, not
snappy — and the 64K minimum eats further into that already-thin quant's headroom. †3

## 5. Recommended concrete stack

Given your hardware and that Deep Research is the heavier workload:

**Hybrid is the benchmark-justified answer, not "all local" or "all cloud":**

1. **Local model on the 4090** for the high-frequency, cheap parts of the loop — web-page
   extraction/summarization, tool-call formatting, simple sub-agent research legs. Best fit:
   **Qwen3-Coder 32B Q4_K_M** (best tool-calling reliability + speed benchmarks for a single 24GB card) or
   **Gemma 4 26B-A4B** if you want more headroom and higher raw tok/s for parallel subagents. †6 Set via
   Hermes's native custom-endpoint path: if your local server has exactly one model loaded, `/model custom`
   auto-detects it — you can also set `provider: custom` in config.yaml; it's a first-class provider, not an
   alias, and this works with Ollama, vLLM, llama.cpp server, SGLang, LocalAI, and others.

2. **Cloud model as the "planner brain"** for the actual Deep Research orchestration step (multi-turn
   coherence, long synthesis, citation-quality writing) — route through **Hermes 4 405B or Hermes 4.3 36B
   via OpenRouter/Nous Portal** if you want to stay in the Hermes lineage and avoid over-refusal on research
   topics (RefusalBench numbers above), or a frontier closed model if raw reasoning quality matters more
   than openness for a given task. †5 Hermes 4 405B on OpenRouter runs $1/M input, $3/M output tokens with a
   131,072 token context window — cheap enough that even heavy daily Deep Research runs stay in the
   few-dollars range, and it clears the 64K floor with room to spare.

3. **Local embedding/session-search sidecar**: run a small embedding model in the VRAM headroom left by
   whichever 20-32B model you pick, and point Hermes's memory search at it: once you get your preferred
   embedding model up on an endpoint with llama.cpp, add auxiliary `session_search` config pointing at it —
   this keeps memory/session search local even if the main model is cloud.

4. **Switching is trivial** — you can switch providers at any time with `hermes model` — no lock-in, so
   start local-only, and only bring in the cloud planner model once you feel Deep Research quality
   plateauing on the 32B local model (it will, especially on multi-hop synthesis across 10+ sources).

**Bottom line**: your 4090 is genuinely well-suited to *native web search* end-to-end locally (Qwen3-Coder
32B or Gemma 4 26B-A4B handle single/few-tool-call lookups fine at 24GB). †6 For *Deep Research*, the
operational reality — per the benchmark note that the real benchmark is operational: can the model read a
file, call the terminal, preserve the requested format, recover from a failed tool, and complete a second
turn without drifting — favors offloading the top-level planning to a cloud Hermes-4/405B or frontier
model, since 24GB simply can't host a model in the same reasoning tier as what a $1-3/M-token API gives
you for a workload that's inherently bursty rather than always-on.
