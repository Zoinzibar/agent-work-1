# Updated workflow: native Web Search & Deep Research on Hermes Agent
## Arch Linux / single RTX 4090 (24 GB) — revision 2026-09-27

> **Lineage.** [`initial-agent-research.md`](initial-agent-research.md) proposed the workflow.
> [`claim-verification-analysis.md`](claim-verification-analysis.md) graded it (2026-09-26).
> [PR #4](https://github.com/Zoinzibar/agent-work-1/pull/4) / [`CRITICAL_REVIEW.md`](CRITICAL_REVIEW.md)
> refused to treat that correction as ground truth. **This file is the proposed workflow that
> applies that review**, after a primary-source pass on 2026-09-27. It replaces the review's
> disclaimer-on-top-of-the-old-draft. It is not a new scorecard of all 33 original claims.
>
> **This file is not "safe to act on."** It is corrected against the sources listed in §11,
> fetched 2026-09-27, with assumptions stated. Model IDs, prices, and catalog fit still move.
> Run §12 before downloading or subscribing. If `hermes-agent.nousresearch.com` does not
> resolve, stop — do not debug a CLI from this document alone.

**How to read a label.**

| Label | Means |
| --- | --- |
| **Re-checked** | A primary page was fetched for this revision on 2026-09-27. |
| **Derived** | Computed here from a fetched `config.json` or a published price. Assumptions are named. |
| **Carried** | Taken from the 2026-09-26 analysis and **not** re-fetched. Use it as a lead, not as a fresh measurement. |
| **Judgment** | A role assignment (which tier does what). Not a benchmark ranking. |
| **Withdrawn** | A number in the previous edition that this revision does not carry. |

A bare `§N` is this file. Analysis sections are "analysis §N".

---

## 0. TL;DR

The architecture still holds: do cheap, frequent research steps locally; send multi-hop planning
and citation-quality synthesis to a cloud model whose tool calling you have actually tested.
What changed in this revision is the evidence under the specific names.

| Layer | Previous corrected edition | This revision |
| --- | --- | --- |
| Does Hermes Agent exist? | Cited its own docs. PR #4 called that circular. | **Re-checked.** Public repo [`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent) and the docs index both responded on 2026-09-27. Still: if they 404 on your machine, stop. |
| Local weight | Qwen3.8-27B as "default local pick", AA Index 52 vs 38, sourced from SEO blogs | **Exists** — [`Qwen/Qwen3.8-27B`](https://huggingface.co/Qwen/Qwen3.8-27B), SHA `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, last modified 2026-08-14. **AA 52 vs 38 is withdrawn** (not on the model card; not re-read from Artificial Analysis). Role is a **judgment**, not a ranking. |
| Throughput alternative | Gemma 4 26B-A4B, "✅ ~17.5 GiB at 32K" | **Exists** — [`google/gemma-4-26B-A4B-it`](https://huggingface.co/google/gemma-4-26B-A4B-it). The old fit verdict is **withdrawn**. KV is now a derived range (§4.1), not a measured fit. Speed figures are not carried. |
| 70B fallback | Removed. Correctly. | Still removed. 20 GiB of fp16 KV at 64K is carried geometry; it cannot sit beside 70B weights in 24 GiB. |
| Planner | "A current frontier or frontier-adjacent model" | **Named IDs** from vendor docs fetched today (§5). Not Hermes 4 405B. Confirm the route accepts `tools` with `scripts/test_tools.py` before you build on it. |
| Search ladder | Keyed primary, keyless ring as failover, xAI separate | Still the plan. The live backend table is wider than the 2026-09-26 writeup (§2.2). |
| Safety claim | PR #4 removed "safe to act on" and added a draft §5.1 | Kept removed. Security section rewritten against the code-execution and security docs, which are more specific than the review assumed. |

Sequencing ("validate the planner early") stays in §5. It is **advisory**, the same status as
analysis M18. It is not a scored correction. It is in the TL;DR because it changes what you do
first, not because it was graded.

---

## 1. What you are configuring

**Re-checked.** Hermes Agent is Nous Research's open-source agent. The docs index describes it
as a terminal-native agent with a desktop app, a messaging gateway, and an ACP surface, working
with Nous Portal, OpenRouter, OpenAI, Anthropic, Google, or any OpenAI-compatible endpoint,
including local models. Repo license on the GitHub landing page: MIT.

Point-in-time pin, not a version to install blindly: commit `2f14d5e` was HEAD when the repo
page was fetched on 2026-09-27. Pin the commit you actually install. HEAD will have moved.

```bash
# Official installer. Read the script before piping it to a shell.
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh -o /tmp/hermes-install.sh
less /tmp/hermes-install.sh
bash /tmp/hermes-install.sh
```

Commands confirmed on the repo README: `hermes`, `hermes model`, `hermes tools`, `hermes setup`,
`hermes doctor`, `hermes update`. `hermes setup --portal` is the paid Nous Portal path (Tool
Gateway). Switching providers is `hermes model` — **carried** as M15; the README still documents
`hermes model`.

**64K context.** The local-models doc, fetched today, says every recommended catalog model gets
at least a 64K window, and that Hermes does not offer builds below 4-bit. The analysis's
"rejected at startup, upstream issue #53347" is **carried** — that issue was not re-opened this
pass. If a model is refused, run `hermes doctor` and read the error. Do not assume the issue
number is still the right citation.

---

## 2. Workflow 1 — native web search

**Re-checked** against the [web-search doc](https://hermes-agent.nousresearch.com/docs/user-guide/features/web-search).
Web search is built in: `web_search` and `web_extract`. No custom skill is required for the
basic path.

### 2.1 Setup

```bash
hermes tools            # Web Search & Extract → pick a provider; the wizard stores the key or URL
hermes setup --portal   # paid Portal path: gateway tools, no per-tool keys
```

### 2.2 Provider ladder

The live table is wider than the 2026-09-26 edition. Backends now listed include Firecrawl
(marked default), SearXNG, Brave, DDGS, Exa, Parallel, Tavily, Perplexity, Keenable, xAI, and
OpenAI Native. Plan around the ones below. The others are available; they are not a
recommendation.

1. **Keyed primary.** Firecrawl is the documented default (search and extract; free tier 500
   credits/month; keyless only when that backend is explicitly selected). Or self-host SearXNG
   for search and pair it with a keyed extractor. SearXNG is search-only. It is not air-gapped:
   a self-hosted instance still queries live engines, and those engines see the query.
2. **Keyless ring is failover, not the plan.** With no credentials, requests rotate across Exa,
   Parallel, Firecrawl, and Keenable until one serves or all are throttled. The doc calls this
   strictly last-resort. Disable it with `web.keyless_fallback: false` if you do not want silent
   failover onto anonymous tiers.
3. **xAI is a separate backend.** **Re-checked:** results are LLM-generated titles, descriptions,
   and URL choices, not index-backed results. Do not cite them blind. The older claim that xAI
   is excluded from the auto-detect chain was **not** in the portion fetched today — set
   `web.backend` explicitly if you use it, and do not assume the exclusion still holds.
4. **Parallel is not xAI.** Parallel is its own index-backed search/extract provider and a
   keyless-ring member. The brief's "Parallel/xAI routing through Grok" remains wrong (analysis
   F8).

### 2.3 Behaviour to design around

**Re-checked.**

- `web_extract` does not summarise. Default budget is 15,000 characters
  (`web.extract_char_limit`, clamped 2,000–500,000). Over budget, the tool returns a head+tail
  window (~75% head / ~25% tail) plus a `[TRUNCATED]` footer. The full text is on disk; the
  footer names the `read_file` call. The omitted part is the **middle**, not only the tail.
  Either raise the limit or page the file. There is no eval in this repo that the agent
  reliably pages.
- Identical concurrent searches are coalesced into one backend request. Extracts are cached
  under `~/.hermes/cache/web/` across CLI, gateway, cron, and subagent processes. Ten
  "independent" subagents on the same query are not ten backend calls. For an eval, vary the
  query or account for the cache. Do not assume a config flag to disable it — none was in the
  fetched section.

These two bullets are load-bearing and were previously unscored ("not in the brief"). They are
**re-checked** against the doc, not against a running install.

---

## 3. Workflow 2 — Deep Research is composed, not switched on

**Carried, and consistent with the docs index fetched today:** the index has no "Deep Research"
product page. Assemble the loop from the features below. A community skill may exist; it is not
a Nous mode. That skill was not re-fetched.

- **`delegate_task`** — isolated subagents; only the final summary returns to the parent.
  **The 3-vs-10 contradiction is still live**, re-checked via the current docs search:
  the features overview says 3 concurrent by default; the configuration reference says
  `delegation.max_concurrent_children` defaults to 3; the delegation guide says up to 10 by
  default. Read the value on your build. Do not hard-code 10. Batches over the cap return a
  tool error rather than truncating (configuration doc). Nested depth defaults to flat
  (`max_spawn_depth` 1). Raising both multiplies spend (the docs' own example: 3×3×3 = 27
  leaves).
- **`execute_code`** — one inference turn, Python on the host, only `print()` returns.
  See §6 before enabling it. Timeout default 300s, stdout cap 50 KB, 50 tool calls per
  execution. All three are configurable.
- **Your documents** are a native capability. NotebookLM-via-MCP is **carried** as third-party
  browser automation, not a Hermes feature. Treat it as a credential-bearing browser driver.
- **Cron** — **carried:** scheduled output goes to messaging platforms, and every run bills the
  full model cost. Not re-fetched.
- **MCP** — native. Community servers are unsigned code. Pin a commit and read it (§6).
- **Token appetite** — directionally certain (one context per workstream, plus synthesis). The
  previous edition's "Qwen3.8-27B emitted 160M output tokens on the AA agentic index" is
  **withdrawn** here. It was a blog/secondary citation and was not re-read from Artificial
  Analysis. Do not use it to size a budget.

---

## 4. Model choice for one RTX 4090 (24 GB)

### 4.1 Arithmetic

```
KV bytes/token = 2 (K and V) × full-attention layers × kv_heads × head_dim × bytes_per_element
```

fp16/bf16 is 2 bytes. q8_0 is about 1 byte per element, q4_0 about 0.5, **ignoring block
scales** — so quantised KV figures are lower bounds on the cache, not allocator output.
GGUF file sizes below are decimal GB as listed on Hugging Face. llama.cpp and `nvidia-smi`
account in GiB. This file converts only when it sums, and shows both.

`python scripts/kv_cache.py --preset <name>` reproduces the rows. The script's fit line is a
weights+cache sum. It does **not** include the vision projector, CUDA context, or compute
buffers. The managed runtime's green/amber/red badge includes those. That badge is the fit
check that counts; this section is the pre-download estimate.

| Model | What was fetched | KV at 64K, fp16 | Basis |
| --- | --- | --- | --- |
| Qwen3.8-27B | Official `config.json` and model card | **4.00 GiB** (4.295 GB) from full attention only | **Derived.** 16 full-attention layers × 4 KV heads × 256 × 2 bytes × 2. Exactly 64 KiB/token. |
| Qwen3.8-27B linear layers | Same config: 48 `linear_attention` layers, `mamba_ssm_dtype=float32` | **Not zero.** Fixed state, estimated **0.15 GiB**, does not grow with context | **Derived estimate, not measured.** Recurrent state assumed `48 v_heads × 128 × 128 × 4` bytes per layer (3.0 MiB × 48 = 0.141 GiB) plus a conv state of ~6 MiB. Wrong shape would change this term, not the 4 GiB term. |
| Gemma 4 26B-A4B | Official `config.json` and model card | **0.72–1.45 GiB combined** at 64K, the range `scripts/kv_cache.py --preset gemma4-26b-a4b` prints | **Derived range.** Sliding ~0.10–0.20 GiB (window-capped) plus global 0.625 GiB if K=V are unified, 1.25 GiB if they are not. The old "~small / 17.5 GiB at 32K / 192K in 20.9 GB" fit verdict is **withdrawn**. |
| Hermes 4.3 36B | Not re-fetched | 16 GiB if geometry is 64 × 8 × 128 | **Carried** from the Seed-OSS-36B config cited in analysis §8. |
| Llama 3.3 70B | Not re-fetched | 20 GiB if geometry is 80 × 8 × 128 | **Carried.** Enough, with any serious 70B quant, to rule out a fully on-GPU 64K path. |
| Qwen3-Coder-30B-A3B | Not re-fetched | 6 GiB if geometry is 48 × 4 × 128 | **Carried.** |

**Qwen linear layers are not a free zero.** The previous edition assumed DeltaNet contributes
0 KV. The growing cache is the full-attention term only — that part of the assumption matches
the layer-type list. The linear layers still hold a fixed recurrent state. At the estimate
above it is ~0.15 GiB. That does not flip the 24 GiB fit. It does mean "0" was the wrong word.

**Gemma, so the range is not a shrug.** Config: 30 layers, pattern 5 sliding + 1 full, repeated
5 times (25 sliding, 5 full). `sliding_window` 1024. Sliding fields: `num_key_value_heads` 8,
`head_dim` 256. Global fields: `num_global_key_value_heads` 2, `global_head_dim` 512.
`attention_k_eq_v: true`. The model card says global layers use unified Keys and Values.

- Sliding, separate K+V, capped at 1024 tokens: 25 × 8 MiB = **0.195 GiB**, independent of
  context past 1024. If unified K=V applies to sliding layers too, about half of that.
- Global, unified (1×, not 2×), `global_head_dim` 512: **0.625 GiB at 64K**, 2.50 GiB at 256K.
- If "unified" does not mean a 1× cache, double the global term: **1.25 GiB at 64K**.

No official GGUF file size was fetched this pass. Do not add a blog's 15.6 GiB to this range
and call it a measured fit. Download the file listing, convert GB→GiB, add the range, then
leave room for buffers.

**Qwen weight + cache, unit-correct.** There is no official Qwen GGUF. The file table on
[`unsloth/Qwen3.8-27B-GGUF`](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF) at `main`
(fetched as a listing, not a benchmark) included `UD-Q4_K_M` 16.5 GB, `Q4_0` 16.1 GB,
`Q4_1` 17.5 GB, `Q8_0` 29 GB. A plain `Q4_K_M` at 17.1 GB was seen on an older commit, not
on that `main` listing — do not assume it is still published. 16.5 GB decimal = 15.37 GiB.

| Piece | GiB |
| --- | --- |
| Unsloth `UD-Q4_K_M` on `main` (16.5 GB decimal) | 15.37 |
| Full-attention KV, 64K, fp16 | 4.00 |
| Linear-layer state (estimate, 0.147 GiB in the script) | 0.15 |
| **Sum, before projector and buffers** | **19.5** |
| Headroom vs 24 GiB, before those extras | ~4.5 |

A 17.5 GB `Q4_1` file is 16.30 GiB + 4.15 GiB cache/state ≈ 20.5 GiB before buffers. Still
under 24 GiB on this arithmetic, with less room. Re-read the file table the day you download.

q8_0 KV cuts the 4.00 GiB term to about 2.00 GiB; q4_0 KV to about 1.00 GiB, scales ignored.
The previous "22–23 GB all-in (17.8 GB + ~4.6 GB)" mixed units and a blog weight. Prefer the
table above, then the runtime badge.

The tokenizer template on the Hub defaults `reasoning_effort` to **`xhigh`** when thinking is
on. That is a token-budget fact, not a quality claim. For extraction and tool formatting, set
`low` or disable thinking. Leave `xhigh` for the turns that need it.

### 4.2 Shortlist

Role names are **judgments**. They are not "best", and they are not a leaderboard.

| Role (judgment) | ID | Licence | Why it is on the list | What this revision did **not** establish |
| --- | --- | --- | --- | --- |
| Default local weight | [`Qwen/Qwen3.8-27B`](https://huggingface.co/Qwen/Qwen3.8-27B) | Apache 2.0, stated in the model-card frontmatter. [Card](https://huggingface.co/Qwen/Qwen3.8-27B). | Exists. SHA pinned above. 262,144 native context (card; 1,000,000 via YaRN is the card's claim). Tool-call template is in the tokenizer. Computed 64K cache fits beside a ~16–17 GB Q4 file with a few GiB before buffers. Newer than the other two local rows. | That it is the best 24 GiB model. AA Index 52 vs 38. Any tok/s number. That the managed catalog certifies it on your driver. Vendor card numbers (Terminal-Bench 2.1 73.0 vs 63.4 for Qwen3.6-27B; SWE-bench Pro 61.7 vs 53.5) are **vendor-reported, same table** — usable as a within-vendor comparison, not an independent ranking. |
| Throughput candidate | [`google/gemma-4-26B-A4B-it`](https://huggingface.co/google/gemma-4-26B-A4B-it) | Apache 2.0 on the card; the linked licence page resolved to the Apache 2.0 text. Re-read it before production — Google's use-policy URL has moved before. | Card: 25.2B total, 3.8B active, 256K context, native function calling, hybrid attention. Active-parameter count is the *mechanism* reason to expect higher decode speed than a dense 27B. KV range above is small next to weights. | Measured tok/s. The old 149–194 tok/s figure is **withdrawn** from this file (community blog, not re-measured). A numeric on-GPU fit. Confirm the GGUF you download plus §4.1 before treating it as the faster swap-in. |
| Headroom candidate | [`openai/gpt-oss-20b`](https://huggingface.co/openai/gpt-oss-20b) | Apache 2.0 ([OpenAI announcement](https://openai.com/index/introducing-gpt-oss/), 2025-08-05). | Vendor: 21B total / 3.6B active, 128K context, MXFP4 build "only requires 16 GB". That is a vendor memory claim, not a 64K measurement on a 4090. Leaves the most room for an embedding sidecar **if** the claim holds. | Quality. "Cleanest tool calls" was sentiment in the analysis and stays withdrawn. The model is 13 months old as of this revision. |
| Only if you need that tool-call format | `Qwen/Qwen3-Coder-30B-A3B-Instruct` | **Carried.** | Analysis M9: real SWE-bench Verified 50.3–51.6%, not 71.4%. 6 GiB fp16 KV at 64K is tight beside ~18 GB weights. | Not re-fetched. Do not quote the SWE-bench range as fresh. |

**Withdrawn from the recommendation, not from history:** "Qwen3-Coder 32B Instruct" does not
exist (analysis M9). It was not re-404'd this pass — the local existence script hit TLS errors,
which are not 404s (§12). Do not plan on a "Qwen3-Coder-Next 30B Flash" either (analysis:
unconfirmed). No Qwen 4 weights repo was confirmed this pass. Secondary writeups said Qwen 4
was still in training on 2026-09-22; that is not a primary source. Re-query the Hub before you
download.

### 4.3 Ruled out on one 24 GiB card, fully on GPU, at 64K

- **Llama 3.3 70B, any weight quant, as a usable on-GPU path.** Carried: 20 GiB KV plus
  ~21–23 GB of weights. RAM spill can crawl it (§4.4). That is not a fallback you should plan
  research on.
- **Hermes 4.3 36B as the on-GPU reasoning engine.** Carried file size Q4_K_M 21.8 GB
  (20.3 GiB) + 16 GiB KV ≈ 36 GiB before buffers. Needs a second 24 GiB card or an 80 GiB
  card. Keep a Hermes model only as a **policy escape hatch** for topics your planner refuses,
  not as the planner. Low refusal is not a compliance waiver: you are still bound by law and
  by the provider terms. The analysis's RefusalBench restatement (74.60 vs 49.07, both
  non-reasoning) is **carried**, not re-read.
- **Hermes 4 405B as the planner.** See §5. Price is not the reason to keep it.
- **"Claude Opus leads."** Analysis M8 softened this, and it is now also stale as a product
  name. Use the IDs in §5, re-read the vendor page the day you subscribe, and do not import a
  rank order from a roundup blog.

### 4.4 Serving

**Re-checked** on the local-models doc, except the Ollama bullet.

- **Managed llama.cpp runtime** is the default that does not depend on Arch packaging. It
  prices catalog models against your GPU including context, picks the highest-quality build at
  or above 4-bit that fits, guarantees ≥64K for recommended models, grows the window, and
  spills overflow to system RAM (expert weights first, never the attention cache). Amber
  "Uses system RAM" is a supported slow path, not a refusal. Red means the machine cannot run
  that model under the 4-bit floor.
- **Your own llama-server** is detected if it is already listening. For a manual build, set
  the context explicitly (`--ctx-size 65536`) and confirm CUDA is the backend that actually
  ran (§9).
- **vLLM / SGLang** remain the docs' concurrent-serving suggestion. TensorRT-LLM is still not
  the documented path (analysis M13, carried).
- **Ollama** — **carried:** set `OLLAMA_CONTEXT_LENGTH=64000` and match `config.yaml`.
  `/api/show` reports the model's maximum context, not the effective `num_ctx`. The "10–15%
  overhead" figure stays withdrawn; the analysis's central estimate was 2–8% and was not
  re-measured.
- **Wiring.** If one model is loaded, `/model custom` auto-detects it. Otherwise
  `provider: custom` in `config.yaml`.

---

## 5. Concrete stack

**Judgment**, except where a label says otherwise.

1. **Local tier.** `Qwen/Qwen3.8-27B`, community quant `unsloth/Qwen3.8-27B-GGUF` `UD-Q4_K_M`
   (16.5 GB on the `main` listing fetched today — there is no official GGUF), for extraction,
   tool-call formatting, and short subagent legs. Pin the Hub SHA in §4.2 when you download;
   if `lastModified` is no longer 2026-08-14, re-read the card before trusting §4.1. Set
   `reasoning_effort` to `low` (or thinking off) for those legs. Swap in Gemma 4 26B-A4B only
   after you have added *your* GGUF size to the §4.1 range and the runtime badge is green.
   Do not swap it in because a blog measured 194 tok/s.
2. **Planner tier.** Not Hermes 4 405B. On 2026-09-27 the OpenRouter page still listed it at
   **$1 / $3 per million**, 131K context, and mirrored an Artificial Analysis panel: Terminal-Bench
   Hard 11.4%, τ²-Bench Telecom 22.2%, AA-LCR 22.3%, HLE 10.9%, non-hallucination rate 5.5%
   ([OpenRouter](https://openrouter.ai/nousresearch/hermes-4-405b), which links
   [the AA model page](https://artificialanalysis.ai/models/hermes-4-llama-3-1-405b-reasoning)).
   **The AA page itself was not re-fetched**, so index version and effort are not pinned.
   Treat the panel as a generation-gap signal from a gateway mirror, not as a precise rank.
   The largest public app on that page was a roleplay front-end. A heavy 500K-in / 100K-out
   call at $1/$3 is still $0.80. That price is not a reason to keep a weak planner.

   Named candidates, each with tool use stated on the vendor page fetched 2026-09-27. Prices
   are list prices, not cached prices. Re-read them the day you subscribe.

   | Role (judgment) | ID | List price / 1M in, out | Context | Source |
   | --- | --- | --- | --- | --- |
   | Default planner | `claude-opus-5-5` | $4 / $20 | 1M | [Anthropic models overview](https://platform.claude.com/docs/en/models/overview). Their own "start here for most workloads". Tool use listed for all current models. |
   | Cheaper daily planner | `claude-sonnet-5` | $2 / $10 | 1M | Same page. |
   | OpenAI balance pick | `gpt-6-sol` | $2 / $10 | 1.05M | [OpenAI models](https://developers.openai.com/api/docs/models). Tools listed: functions, web search, file search, computer use. |
   | Lower list price, intro rate | `gemini-3.8-flash` | $0.75 / $3.75 through 2026-12-31 | 1,048,576 in / 65,536 out | [Model page](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash) (function calling: supported) and [latest-model](https://ai.google.dev/gemini-api/docs/latest-model) (intro price). Standard pricing starts 2027-01-01; the post-intro number was not in the section fetched — read the pricing page that day. |

   Harder-than-default, not the default: `claude-fable-5-1` and `gpt-6-astra` are both $10 / $50
   on those same pages. Use them when a cheaper ID fails your own tasks, not as the steady
   planner.

   **Before any of these is "the" planner**, run one live tool call:

   ```bash
   python scripts/test_tools.py --provider anthropic --model claude-opus-5-5
   # prints the request, sends nothing
   python scripts/test_tools.py --provider anthropic --model claude-opus-5-5 --send
   # sends only if ANTHROPIC_API_KEY is set; the key is not printed
   ```

   OpenRouter and Nous Portal are OpenAI-compatible. Point `--base-url` at the gateway and
   `--provider openai`. A 400 that says tools are unsupported means that route is not your
   planner, whatever the marketing page says. Hermes 4.3 36B remains the local escape hatch
   for short-context legs you are willing to run slowly or on a bigger card — not the
   reasoning engine on this 4090.
3. **Web search.** §2.2. Keyed Firecrawl, or SearXNG plus a keyed extractor. Keyless ring as
   automatic failover only. xAI only if you accept the citation caveat and set the backend
   explicitly.
4. **Memory.** **Carried, not re-verified on an install:** prefer a memory-provider plugin
   (the analysis named LanceDB, Honcho, Mem0) aimed at a local OpenAI-compatible embedding
   endpoint, so session search stays local when the planner is cloud. The brief's
   `auxiliary: session_search` block is version-sensitive. A single practitioner blog is not
   enough to declare the slot removed. Check your installed config before wiring it.
5. **Sequencing (advisory).** Stand up web search locally first — the §4.2 weight is the part
   least likely to be the bottleneck, and it costs a download rather than a subscription.
   Then validate the planner on a real multi-hop task (many sources, a failed tool call, a
   format that has to survive a second turn) **before** you invest in cron, MCP, or a second
   local quant. This inverts the brief's "add the planner when quality plateaus." It is
   advice, not a graded claim.

---

## 6. Security

PR #4 was right that the previous edition had no threat model. It was wrong that the docs are
silent. The [code-execution doc](https://hermes-agent.nousresearch.com/docs/user-guide/features/code-execution)
and the [security doc](https://hermes-agent.nousresearch.com/docs/user-guide/security) were
fetched for this section. This is not a pentest.

**`execute_code` is a child process on the agent host, not a container, unless you chose a
remote terminal backend.** What the doc actually guarantees:

- Environment scrubbing. Names containing `KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `CREDENTIAL`,
  `PASSWD`, or `AUTH` are stripped. A small fixed set of `HERMES_*` names is passed. Anything
  else you need must be allowlisted, and Hermes-managed provider credentials cannot be
  re-allowed that way.
- Tool whitelist inside the script: no recursive `execute_code`, no `delegate_task`, no MCP.
  `terminal()` **is** available, foreground only, and goes through the same approval path as a
  normal terminal call.
- Limits: 300s, 50 KB stdout (full output under `~/.hermes/cache/exec/`), 50 tool calls.
- `code_execution.mode: project` (the default) runs in the session working directory. A script
  can `open(".env")`. `strict` uses a temp directory and Hermes's own interpreter. Switching
  mode does not change the credential scrub or the tool whitelist.

What to do:

- Leave `approvals.mode` at `smart` or `manual`. `off`, `hermes --yolo`, and `/yolo` disable
  dangerous-command prompts. The doc says YOLO does not bypass a hardline blocklist; do not
  treat that as a sandbox.
- For a research agent that will execute code, prefer the Docker terminal backend over the
  local one, and do not mount host secrets into it. Container isolation is a documented
  backend, not the default for `execute_code`.
- Set `code_execution.mode: strict` unless the script must import the project.
- Cron and other unattended sessions default `cron_mode` / `unattended_mode` to `deny` on
  dangerous commands. Leave that deny.

**`web_extract` is untrusted content.** The 15k window shows head and tail. A prompt injection
can sit in the visible head, or in the middle that the agent later pages. Treat extracted
pages as data. Do not raise the char limit to 500,000 and then let the same model both read
the page and approve shell commands.

**MCP and skills.** `hermes skills install …` and third-party MCP servers (including a
NotebookLM browser driver) are unpinned code with whatever credentials the browser or the
server holds. Pin a git SHA, read the server, and do not point one at a logged-in browser
profile you care about. The security doc describes MCP credential filtering; filtering is not
a review of the server.

**SearXNG.** Bind it to localhost unless you intend to run a public metasearch. It still sends
queries to the engines it is configured to use.

**Installer.** The official one-liner is `curl | bash`. Read the script first (§1).

---

## 7. Cost

Local is not free, and hybrid is not automatically cheaper. No token split was measured. Fill
in your own rate and purchase price. The examples are arithmetic, not a quote.

**Power, upper bound.** RTX 4090 board power is 450 W TDP. Measured draw during inference is
lower and was not measured here. Daily energy at a flat 450 W is `hours × 0.45 kWh`.

| Assumption (labeled, not measured) | Energy | At $0.15/kWh | At $0.30/kWh |
| --- | --- | --- | --- |
| 2 h/day at 450 W (TDP ceiling) | 0.90 kWh | $0.14 | $0.27 |
| 8 h/day at 300 W (illustrative average — **not measured**) | 2.40 kWh | $0.36 | $0.72 |

Amortise the card yourself: `purchase_price / (years × 365)` per day, whether or not you run a
job. A $1,800 card over 3 years is about $1.64/day. That number is an illustration. Idle VRAM
has an opportunity cost only if you would otherwise have used the card for something else —
usually you would not. Do not add $1.64 to every research run and call the GPU "more expensive
than the API."

**One heavy planner call, list price, 500K input + 100K output, no cache.** Derived from §5
prices.

| Route | This call |
| --- | --- |
| Hermes 4 405B at $1 / $3 | $0.80 |
| `gemini-3.8-flash` intro ($0.75 / $3.75) | $0.75 |
| `claude-sonnet-5` or `gpt-6-sol` at $2 / $10 | $2.00 |
| `claude-opus-5-5` at $4 / $20 | $4.00 |
| `claude-fable-5-1` or `gpt-6-astra` at $10 / $50 | $10.00 |

Ten such calls a day on Opus 5.5 is $40 before cache, not "a few dollars." Cache and batch
discounts change this; they are provider-specific and not applied above. Hybrid beats
all-cloud only if the local tier actually absorbs the bulk of tokens. Log input, output, and
cached tokens per job for a week before you believe that it does.

---

## 8. Failure modes

| Symptom | Likely cause | Detection | Mitigation |
| --- | --- | --- | --- |
| Process killed, or amber "Uses system RAM" | Weights + KV + buffers > GPU memory | `nvidia-smi`; runtime badge | Smaller quant, q8_0 KV, shorter window, or a smaller model. Re-run `scripts/kv_cache.py` against the file you downloaded. RAM spill is a crawl, not a fix. |
| ~2 tok/s, GPU idle, RAM busy | Expert weights spilled to system RAM | `nvidia-smi` util low, RAM high | Do not use that model for the local tier. |
| Subagents return the same page | Query coalescing and `~/.hermes/cache/web/` | Identical queries in the log | Vary the query for evals. Do not invent a cache-disable flag that was not in the doc. |
| Synthesis misses the middle of a paper | 15k head+tail extract | `[TRUNCATED]` footer | Page the on-disk file, or raise `web.extract_char_limit` and still treat the text as data. |
| Planner returns 400 on tools | Gateway route does not accept `tools` | `scripts/test_tools.py --send` | Change ID or provider. Do not debug prompts first. |
| `delegate_task` errors on a batch of 10 | Installed cap is 3, not 10 | The tool error names the cap | Read `delegation.max_concurrent_children`. Do not "fix" it by raising depth and width together. |
| Agent runs shell from a research script | `execute_code` can call `terminal()` | Approval prompt, or no prompt if YOLO | §6. Docker backend, `strict` mode, approvals on. |
| CUDA "no device" after a kernel upgrade | Arch rolling release, module not rebuilt | `nvidia-smi` fails | §9. DKMS driver, reboot, then confirm the llama.cpp backend is CUDA rather than Vulkan. |

---

## 9. Arch Linux

The title is not decorative. This is the minimum that matches the Arch wiki page fetched
2026-09-27, not a 2024 driver pin.

The RTX 4090 is Ada Lovelace. The [NVIDIA wiki page](https://wiki.archlinux.org/title/NVIDIA)
lists Ada as supported by `nvidia-open` (stock `linux`), `nvidia-open-lts`, or
`nvidia-open-dkms` (any kernel), **or** the proprietary `nvidia-580xx-dkms` AUR package. Do
not install the `.run` from NVIDIA's website; the wiki warns that it will not upgrade with
the rest of the system. Do not pin "driver 555+" or "CUDA 12.6" from the review draft — those
numbers are not what the current wiki says.

```bash
# Stock kernel. Use nvidia-open-dkms instead if you are not on the `linux` package.
sudo pacman -S nvidia-open nvidia-utils
nvidia-smi
```

After a kernel upgrade, a non-DKMS module breaks until it is rebuilt. If `nvidia-smi` fails,
fix that before you touch models.

**llama.cpp.** Hermes's managed runtime downloads its own engine. Prefer that unless you need
flags it does not expose. For a manual build, Arch's `ggml` package is built with
`-DGGML_CUDA=ON` (packaging discussion on the wiki talk page, 2026), but a Vulkan backend can
still be the one that gets selected. The `llama.cpp-cuda` AUR package has been flagged
out of date. Verify, do not assume:

```bash
nvidia-smi   # watch this during a short generate; util should leave 0%
```

If the GPU stays idle, you are on CPU or on a backend that is not actually running the model.
Rebuild from [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) with `-DGGML_CUDA=ON`
and confirm the log names CUDA. A venv (`python -m venv`) is the right place for any Python
client; do not install those packages into the system interpreter.

---

## 10. Traceability

### 10.1 From the brief, unchanged in substance

| Brief | Analysis | This file |
| --- | --- | --- |
| Parallel/xAI as one Grok route | F8 ❌ | Still split. xAI citation caveat re-checked. "Not in auto-detect" not re-confirmed (§2.2). |
| Keyless ring as the plan | F5 ✅ | Still failover. Ring members re-checked. |
| SearXNG as an air-gapped skill | F9 ⚠️ | Still search-only, not air-gapped. Now also a binding/privacy note (§6). |
| "Deep Research" as a mode | F10 ⚠️ | Still composed. Docs index has no such product page. |
| Qwen3-Coder 32B / 71.4% SWE-bench | M9 ❌ | Still deleted. Not re-404'd this pass. |
| Llama 3.3 70B IQ2_XXS fallback | M14 ❌ | Still deleted. |
| Hermes 4 405B as planner | analysis §3.4 | Still rejected. Price and AA mirror re-checked on OpenRouter. AA run page not re-fetched. |
| Start local-only; add planner later | M18 advisory | Still inverted, and **labeled advisory** so it is not smuggled in as a scored fix. |

### 10.2 What PR #4 required, and what this revision did

| Review item | Disposition |
| --- | --- |
| 1. Hermes docs might be circular | **Resolved for 2026-09-27.** Repo and docs index both responded. No WARC and no HTML body hash — a SHA pin of the docs HTML was not produced. If the origin 404s later, the resolution expires. |
| 2. Qwen3.8 / Gemma 4 might be the next hallucinated names | **Resolved as existence.** Both Hub repos and `config.json` files were fetched. **Not resolved as "best."** AA 52 vs 38 withdrawn. |
| 3. KV math hides DeltaNet and mixes units | **Addressed.** DeltaNet state estimated, not zero. Gemma fit verdict withdrawn and replaced with a derived range. Script presets match §4.1. |
| 4. "Safe to act on" | **Stays removed.** |
| 5. New claims unscored; superlatives snuck back in | Load-bearing new claims are labeled re-checked or carried. Role names are marked judgment. "Best local pick" is not used. |
| 6. Rubric subjectivity | Not re-graded. This file does not emit a new 17/13/3. |
| 7. Planner was "frontier-adjacent" | **Addressed.** Four named IDs, vendor URLs, list prices, and `scripts/test_tools.py`. |
| 8. No Arch steps | **Addressed** in §9, from the current wiki, not from the review's driver pin. |
| 9. Cost hand-waving | **Addressed** as formulas plus labeled examples. Hybrid savings explicitly unmeasured. |
| 10. Tier-2 sources used as primary | §11 splits tiers. Blog-only figures (AA 52, 149 tok/s, 160M tokens, 2.3 GB/32K) are withdrawn. |
| 11. No failure modes | §8. |
| 12. Licence and low-refusal ethics | Licence column in §4.2. Escape-hatch note in §4.3. |
| 13. No freshness command | §12. The existence script no longer treats a TLS error as "model does not exist." |
| 14. AA 52 vs 38 might be mis-attributed | **Withdrawn** rather than re-defended. Vendor-card comparisons are labeled vendor-reported. The 405B panel is labeled as an OpenRouter mirror, index version unpinned. |

---

## 11. Sources

Access date for every row fetched this pass: **2026-09-27**. No HTML body hashes. No WARC.

### Tier 1 — used for a claim in this file

| Claim | URL |
| --- | --- |
| Framework exists; installer; command names | https://github.com/NousResearch/hermes-agent |
| Docs index | https://hermes-agent.nousresearch.com/docs/llms.txt |
| ≥64K, 4-bit floor, RAM spill, managed runtime | https://hermes-agent.nousresearch.com/docs/user-guide/local-models |
| Backends, keyless ring, 15k extract, coalescing, xAI caveat | https://hermes-agent.nousresearch.com/docs/user-guide/features/web-search |
| `execute_code` host process, scrubbing, limits | https://hermes-agent.nousresearch.com/docs/user-guide/features/code-execution |
| Approvals, YOLO, container isolation | https://hermes-agent.nousresearch.com/docs/user-guide/security |
| Delegation cap contradiction (overview vs config vs guide) | https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation and the configuration / overview pages as returned by docs search |
| Qwen3.8-27B existence, SHA, licence, template, geometry | https://huggingface.co/Qwen/Qwen3.8-27B and its `config.json` |
| Gemma 4 26B-A4B existence, card, geometry, Apache 2.0 text | https://huggingface.co/google/gemma-4-26B-A4B-it and https://ai.google.dev/gemma/apache_2 |
| gpt-oss-20b announcement | https://openai.com/index/introducing-gpt-oss/ |
| Hermes 4 405B price and mirrored AA panel | https://openrouter.ai/nousresearch/hermes-4-405b |
| Claude planner IDs and prices | https://platform.claude.com/docs/en/models/overview |
| OpenAI planner IDs and prices | https://developers.openai.com/api/docs/models |
| Gemini 3.8 Flash ID, function calling, intro price | https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash and https://ai.google.dev/gemini-api/docs/latest-model |
| Arch driver packages | https://wiki.archlinux.org/title/NVIDIA |

### Tier 2 — file listing or community quant, not a benchmark

| Item | URL | Used for |
| --- | --- | --- |
| Unsloth Qwen3.8 GGUF sizes | https://huggingface.co/unsloth/Qwen3.8-27B-GGUF | File sizes only. Not tok/s, not quality. |

### Not used, on purpose

`codersera.com`, `kingy.ai`, `quesma.com`, `atomic.chat`, `benchlm.ai`, `modelgrep.com`,
`morphllm.com`, and the practitioner blog that declared `auxiliary.session_search` removed.
Those were the inputs to the previous edition's volatile numbers. They are not cited here.

### Carried, not re-fetched

Analysis §8 remains the trail for Hermes 4.3 file sizes, Seed-OSS geometry, Llama geometry,
Qwen3-Coder-30B-A3B SWE-bench, the Ollama `num_ctx` trap, and issue #53347. If you act on one
of those, open the URL in analysis §8 first.

---

## 12. Checklist

Run this before a download or a subscription. A TLS error is not a 404.

- [ ] **Origin still up.** `curl -fsSL -o /dev/null -w '%{http_code}\n' https://hermes-agent.nousresearch.com/docs/llms.txt` returns 200. If it does not, stop.
- [ ] **Hub SHA.** `python scripts/check_model_existence.py` — transport errors print as transport errors. A missing `Qwen/Qwen3.8-27B` or a SHA other than `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` means re-read §4 before downloading.
- [ ] **KV.** `python scripts/kv_cache.py --preset qwen3.8-27b` and `--preset gemma4-26b-a4b`. Compare to §4.1. Then trust the runtime badge over the script.
- [ ] **Catalog badge.** Settings → Providers → Local Models, on your driver. Green means on-GPU. Amber means a crawl. Red means pick another weight.
- [ ] **Reasoning effort.** Confirm the local server is not silently on `xhigh` for extraction legs.
- [ ] **Delegation cap.** Print `delegation.max_concurrent_children`. Do not assume 3 or 10.
- [ ] **Planner tool call.** `python scripts/test_tools.py --provider <anthropic|openai|gemini> --model <id>` then the same with `--send` and the key in the environment. A 400 on `tools` ends that candidate.
- [ ] **Prices.** Re-open the three vendor pages in §11. Gemini's intro rate ends 2026-12-31.
- [ ] **Approvals.** `approvals.mode` is `smart` or `manual`. YOLO is off. `code_execution.mode` is `strict` unless you need project imports.
- [ ] **Arch.** `nvidia-smi` works after the latest kernel. A short generate moves GPU util off zero.
- [ ] **Do not revive** Qwen3-Coder 32B, Llama 3.3 70B as an on-GPU 64K fallback, or Hermes 4 405B as the planner.

*Deliberately not carried from analysis §7: the Hermes 4.3 commit-date vs blog-date discrepancy. Nothing here depends on it.*

---

*This revision supersedes the disclaimer draft that PR #4 left in this file. The review's
concerns are the source of the new sections; the primary pages in §11 are the source of the
claims. Where those disagree with the review — framework existence, model existence, the
`execute_code` threat model — the fetched page wins, and the disagreement is named in §10.2.*
