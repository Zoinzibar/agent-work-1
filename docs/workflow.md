# Hermes Agent: web search and deep research on Arch Linux with one RTX 4090 (24 GB)

**Last verified: 2026-09-27.** Model IDs, prices and catalog fit change faster than anything else
here. Run the [checklist](#10-checklist-before-you-download-or-subscribe) before downloading a
model or paying for a subscription. If `hermes-agent.nousresearch.com` does not resolve, stop:
don't try to debug a CLI from this document alone.

Sources, Hub SHA pins, unverified leads and known-false claims are in [`sources.md`](sources.md).

**Labels used below**

| Label | Meaning |
| --- | --- |
| **Verified** | A primary page (vendor docs, official repo, Hub API or `config.json`) was fetched on the "last verified" date. |
| **Derived** | Computed here from verified inputs. The assumptions are stated. `scripts/` reproduces it. |
| **Unverified** | Last checked 2026-09-26 or earlier and not re-fetched since. Treat it as a lead; the URL is in [`sources.md`](sources.md#unverified-leads). |
| **Judgment** | A role assignment (which tier does which job). Not a benchmark ranking. |

---

## 0. Summary

Run cheap, frequent research steps (extraction, tool-call formatting, short subagent legs) on a
local model. Send multi-hop planning and synthesis where citations matter to a cloud model, and
only after you have tested its tool calling yourself.

| Layer | Pick | Status |
| --- | --- | --- |
| Framework | Hermes Agent ([`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent), MIT) | Verified |
| Local weight | [`Qwen/Qwen3.8-27B`](https://huggingface.co/Qwen/Qwen3.8-27B), Unsloth `UD-Q4_K_M` GGUF | Verified to exist; role is a judgment |
| Local alternatives | Gemma 4 26B-A4B (throughput), gpt-oss-20b (headroom) | Verified to exist; speed not measured |
| Planner | `claude-opus-5-5`, `claude-sonnet-5`, `gpt-6-sol`, or `gemini-3.8-flash` | Verified IDs and prices; **you must test tool calling** (§5) |
| Web search | Keyed Firecrawl, or self-hosted SearXNG plus a keyed extractor; keyless ring only as failover | Verified |
| Not on this card | Llama 3.3 70B, Hermes 4.3 36B as the reasoning engine, Hermes 4 405B as the planner | Derived / verified (§4.3) |

Suggested order (advisory): set up web search and the local model first. Then validate the
planner on a real multi-hop task **before** you invest in cron, MCP or a second quant.

---

## 1. Hermes Agent

**Verified.** Hermes Agent is Nous Research's open-source agent. It runs as a terminal agent, a
desktop app, a messaging gateway, or through an ACP surface for IDEs. It works with Nous Portal,
OpenRouter, OpenAI, Anthropic, Google, or any OpenAI-compatible endpoint, including local models.

```bash
# Official installer. Read the script before running it.
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh -o /tmp/hermes-install.sh
less /tmp/hermes-install.sh
bash /tmp/hermes-install.sh
```

Pin the commit you actually install. (`2f14d5e` was HEAD on 2026-09-27; that was a point in time,
not a recommendation.)

Commands listed in the repo README: `hermes`, `hermes model` (switch provider), `hermes tools`,
`hermes setup`, `hermes doctor`, `hermes update`. `hermes setup --portal` is the paid Nous Portal
path (Tool Gateway, no per-tool keys).

**64K context floor.** **Verified:** every recommended catalog model gets at least a 64K window,
and Hermes offers no builds below 4-bit. **Unverified:** a smaller window is rejected at startup
(upstream issue #53347). If a model is refused, run `hermes doctor` and read the actual error.

---

## 2. Web search

**Verified** against the [web-search doc](https://hermes-agent.nousresearch.com/docs/user-guide/features/web-search).
`web_search` and `web_extract` are built in. The basic path needs no custom skill.

### 2.1 Setup

```bash
hermes tools            # Web Search & Extract → pick a provider; the wizard stores the key or URL
hermes setup --portal   # paid Portal path: gateway tools, no per-tool keys
```

### 2.2 Provider ladder

The doc lists Firecrawl (default), SearXNG, Brave, DDGS, Exa, Parallel, Tavily, Perplexity,
Keenable, xAI and OpenAI Native. Plan around these:

1. **Keyed primary.** Firecrawl is the documented default: search and extract, 500 free
   credits a month, keyless only when that backend is explicitly selected. The alternative is
   self-hosted SearXNG for search plus a keyed extractor, because SearXNG can't extract. It is
   also not air-gapped: it still queries live engines, and those engines see the query.
2. **Keyless ring is failover, not the plan.** With no credentials, requests rotate across Exa,
   Parallel, Firecrawl and Keenable until one serves or all are throttled. The doc calls this
   strictly last-resort. Turn it off with `web.keyless_fallback: false` if you don't want silent
   failover to anonymous tiers.
3. **xAI is a separate backend, and its results are LLM-generated.** Titles, descriptions and URL
   choices come from the model, not from an index. Don't cite them without checking. If you use
   xAI, set `web.backend` explicitly; don't rely on auto-detect behaviour.
4. **Parallel is not xAI.** Parallel is its own index-backed search/extract provider and a member
   of the keyless ring.

### 2.3 Behaviour to design around

- **`web_extract` truncates; it does not summarise.** The default budget is 15,000 characters
  (`web.extract_char_limit`, clamped to 2,000–500,000). Over budget, it returns about 75% head and
  25% tail with a `[TRUNCATED]` footer. The full text is saved to disk, and the footer names the
  `read_file` call to fetch it. **The part left out is the middle.** Either raise the limit or page
  the file.
- **Searches are coalesced, extracts are cached.** Identical concurrent searches become one
  backend request. Extracts are cached under `~/.hermes/cache/web/` and shared across CLI,
  gateway, cron and subagent processes. Ten subagents on the same query are not ten independent
  calls. For evals, vary the query. The docs name no flag to disable the cache.

---

## 3. Deep research is something you compose, not a mode you switch on

The docs index has no "Deep Research" product page. Build the loop from these features:

- **`delegate_task`** runs isolated subagents; only each subagent's final summary returns to the
  parent. **The docs contradict each other on the default concurrency cap:** the features
  overview and the configuration reference say 3, the delegation guide says 10. Read
  `delegation.max_concurrent_children` on your build. A batch over the cap returns a tool error;
  it is not silently truncated. Nesting depth defaults to 1 (`max_spawn_depth`). Raising both
  width and depth multiplies spend: 3×3×3 = 27 leaf agents.
- **`execute_code`** runs Python on the host in a single inference turn, and only `print()` output
  returns to the model. Defaults: 300 s timeout, 50 KB stdout, 50 tool calls, all configurable.
  Read §6 before enabling it.
- **Your own documents** are a native capability. NotebookLM via MCP is a third-party browser
  automation server, not a Hermes feature (unverified). Treat it as a browser driver holding your
  credentials.
- **Cron** (unverified): scheduled output goes to messaging platforms, and every run bills the
  full model cost.
- **MCP** is native. Community servers are unsigned code: pin a commit and read it (§6).
- **Token appetite.** Deep research uses far more tokens than a single search: one context per
  workstream, plus the synthesis. There is no reliable number for this; log your own.

---

## 4. Local model on one RTX 4090 (24 GB)

### 4.1 Memory arithmetic

```
KV bytes/token = 2 (K and V) × full-attention layers × kv_heads × head_dim × bytes_per_element
```

fp16/bf16 = 2 bytes. q8_0 ≈ 1 byte and q4_0 ≈ 0.5 bytes per element; both ignore block scales,
so quantised figures are lower bounds. Hugging Face lists GGUF sizes in decimal GB. llama.cpp and
`nvidia-smi` report GiB. This section converts before it sums.

`scripts/kv_cache.py` reproduces every row below:

- `--preset <name>` for the models in this table.
- `--weights-gb <size>` adds a weights + cache fit line against 24 GiB.
- `--config config.json` works for any model. For hybrid models it counts only
  `full_attention` layers and adds the linear-layer state.

None of these include the vision projector, CUDA context or compute buffers. The managed
runtime's green/amber/red badge does include them, and **that badge is the fit check that
counts.** This section is the estimate you make before downloading.

| Model | KV at 64K, fp16 | Basis |
| --- | --- | --- |
| Qwen3.8-27B, full-attention layers | **4.00 GiB** (4.295 GB); exactly 64 KiB/token | **Derived** from the verified `config.json`: 16 full-attention layers × 4 KV heads × 256 × 2 bytes × 2 |
| Qwen3.8-27B, 48 linear-attention layers | **≈0.15 GiB**, fixed; does not grow with context | **Derived estimate, not measured.** Recurrent state 48 layers × 48 v_heads × 128 × 128 × 4 bytes (`mamba_ssm_dtype` float32) = 0.141 GiB. Conv state ≈7.5 MiB: 48 × kernel 4 × 10240 channels × 4 bytes. Gated DeltaNet convolves Q, K and V, so channels = 2 × 16 × 128 + 48 × 128. A different runtime layout would change this term, but not the 4 GiB term. |
| Gemma 4 26B-A4B | **0.72–1.45 GiB** | **Derived range** from the verified `config.json`, explained below |
| Qwen3-Coder-30B-A3B | 6 GiB, assuming 48 × 4 × 128 | Geometry **unverified**; repo existence verified |
| Hermes 4.3 36B | 16 GiB, assuming 64 × 8 × 128 | **Unverified** (Seed-OSS-36B geometry) |
| Llama 3.3 70B | 20 GiB, assuming 80 × 8 × 128 | **Unverified** geometry. Enough to rule out any on-GPU 64K path |

**Gemma 4 26B-A4B range.** The config has 30 layers: 25 sliding-window and 5 full, in a repeating
pattern of 5 sliding + 1 full. `sliding_window` is 1024. Sliding layers use 8 KV heads with
`head_dim` 256. Global layers use 2 KV heads with `global_head_dim` 512, and
`attention_k_eq_v: true`. The model card says global layers use unified keys and values.

- Sliding layers, separate K and V, capped at 1024 tokens: 25 × 8 MiB = **0.195 GiB** at any
  context length past 1024. Roughly half that if unified K=V also applies to sliding layers.
- Global layers, unified K=V: **0.625 GiB at 64K** (2.50 GiB at 256K).
- If "unified" does not in fact halve the cache, double the global term: **1.25 GiB at 64K**.

No official Gemma GGUF size was verified. Take the size from the file listing, convert it to GiB,
add this range, and leave room for buffers.

**Qwen3.8-27B weights + cache.** There is no official Qwen GGUF. The
[`unsloth/Qwen3.8-27B-GGUF`](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF) `main` listing
(file sizes only) showed `UD-Q4_K_M` 16.5 GB, `Q4_0` 16.1 GB, `Q4_1` 17.5 GB and `Q8_0` 29 GB.

| Piece | GiB |
| --- | --- |
| `UD-Q4_K_M` (16.5 GB decimal) | 15.37 |
| Full-attention KV, 64K, fp16 | 4.00 |
| Linear-layer state (estimate; the script prints 0.148) | 0.15 |
| **Sum, before projector and buffers** | **19.5** |
| Headroom against 24 GiB, before those extras | ~4.5 |

A 17.5 GB `Q4_1` file comes to 16.30 + 4.15 ≈ 20.5 GiB before buffers. That still fits on this
arithmetic, with less room. Re-read the file table on the day you download.

q8_0 KV cuts the 4.00 GiB term to about 2.00 GiB; q4_0 KV to about 1.00 GiB.

**Reasoning effort.** Qwen3.8's chat template defaults `reasoning_effort` to **`xhigh`** when
thinking is on. For extraction and tool formatting, set `low` or turn thinking off.

### 4.2 Shortlist

Role names are **judgments**, not a leaderboard.

| Role (judgment) | ID | Licence | Why it is listed | Not established |
| --- | --- | --- | --- | --- |
| Default local weight | [`Qwen/Qwen3.8-27B`](https://huggingface.co/Qwen/Qwen3.8-27B) | Apache 2.0 | Verified. 262,144 native context (the card claims 1M via YaRN). Tool-call template is in the tokenizer. The 64K cache fits beside a ~16–17 GB Q4 file (§4.1). | That it is the best 24 GiB model. Any tok/s figure. Catalog certification on your driver. The card's Terminal-Bench 2.1 (73.0 vs 63.4 for Qwen3.6-27B) and SWE-bench Pro (61.7 vs 53.5) scores are vendor-reported: fine for comparing Qwen models with each other, not an independent ranking. |
| Throughput candidate | [`google/gemma-4-26B-A4B-it`](https://huggingface.co/google/gemma-4-26B-A4B-it) | Apache 2.0 (re-read the licence page before production) | 25.2B total / 3.8B active, 256K context, native function calling. Its small active-parameter count is the reason to expect faster decoding than a dense 27B. | Measured tok/s. A numeric on-GPU fit. |
| Headroom candidate | [`openai/gpt-oss-20b`](https://huggingface.co/openai/gpt-oss-20b) | Apache 2.0 | 21B total / 3.6B active, 128K context. The vendor says the MXFP4 build "only requires 16 GB". That leaves the most room for an embedding sidecar, if the claim holds at 64K. | Quality. The model dates from 2025-08. |
| Only if you need its tool-call format | [`Qwen/Qwen3-Coder-30B-A3B-Instruct`](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct) | Apache 2.0 | Existence verified. SWE-bench Verified 50.3–51.6% (unverified). 6 GiB KV at 64K is tight beside ~18 GB of weights. | Geometry and benchmark were not re-read. |

Re-query the Hub before downloading. No Qwen 4 weights were confirmed as of the last
verification.

### 4.3 Ruled out: one 24 GiB card, fully on the GPU, at 64K context

- **Llama 3.3 70B, at any quantisation.** 20 GiB of KV plus ~21–23 GB of weights. RAM spill can
  make it run slowly (§4.4), but that is not a fallback to plan research on.
- **Hermes 4.3 36B as the reasoning engine.** Q4_K_M is 21.8 GB (20.3 GiB), plus 16 GiB of KV:
  ≈36 GiB before buffers (unverified sizes). It needs two 24 GiB cards or one 80 GiB card. A
  Hermes model is only worth keeping as a **policy escape hatch** for topics your planner refuses.
  Low refusal does not waive the law or your provider's terms.
- **Hermes 4 405B as the planner.** See §5.

### 4.4 Serving

- **Managed llama.cpp runtime (verified)** is the default, and it doesn't depend on Arch
  packaging. It sizes catalog models against your GPU, including context, and picks the best
  build at 4-bit or above that fits. It guarantees ≥64K for recommended models and grows the
  window as needed. Overflow spills to system RAM, expert weights first, never the attention
  cache. Amber "Uses system RAM" is a supported slow path; red means the machine can't run that
  model at 4-bit or above.
- **Your own `llama-server`** is detected if it is already listening. Set the context explicitly
  (`--ctx-size 65536`) and confirm CUDA is the backend that actually ran (§9).
- **vLLM / SGLang** are the docs' suggestion for concurrent serving. TensorRT-LLM is not a
  documented path (unverified).
- **Ollama (unverified):** set `OLLAMA_CONTEXT_LENGTH=64000` and match it in `config.yaml`.
  `/api/show` reports the model's maximum context, not the effective `num_ctx`.
- **Wiring.** If exactly one model is loaded, `/model custom` auto-detects it. Otherwise set
  `provider: custom` in `config.yaml`.

---

## 5. Full stack

1. **Local tier.** `Qwen/Qwen3.8-27B` as the Unsloth `UD-Q4_K_M` GGUF, used for extraction,
   tool-call formatting and short subagent legs. Pin the Hub SHA
   ([`sources.md`](sources.md#hugging-face-pins)). If `lastModified` has changed, re-read the card
   before trusting §4.1. Set `reasoning_effort` to `low` for these legs. Swap in Gemma 4 26B-A4B
   only once your GGUF size plus the §4.1 range fits and the runtime badge is green.
2. **Planner tier.** Not Hermes 4 405B. OpenRouter lists it at $1 / $3 per million tokens with
   131K context. The Artificial Analysis panel OpenRouter mirrors shows it far behind current
   models: Terminal-Bench Hard 11.4%, τ²-Bench Telecom 22.2%, AA-LCR 22.3%, HLE 10.9%. Read that
   as a generation gap, not a precise rank; the AA page itself was not opened. A low price is not
   a reason to keep a weak planner.

   Candidates below have tool use listed on the vendor page. Prices are list prices without
   caching. Re-read them on the day you subscribe.

   | Role (judgment) | ID | $/1M in, out | Context | Source |
   | --- | --- | --- | --- | --- |
   | Default planner | `claude-opus-5-5` | $4 / $20 | 1M | [Anthropic models](https://platform.claude.com/docs/en/models/overview) |
   | Cheaper daily planner | `claude-sonnet-5` | $2 / $10 | 1M | same page |
   | OpenAI pick | `gpt-6-sol` | $2 / $10 | 1.05M | [OpenAI models](https://developers.openai.com/api/docs/models) |
   | Lowest list price | `gemini-3.8-flash` | $0.75 / $3.75 intro rate until 2026-12-31 | 1,048,576 in / 65,536 out | [Model page](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash), [latest-model page](https://ai.google.dev/gemini-api/docs/latest-model). Standard pricing from 2027-01-01 was not verified. |

   Harder tier: `claude-fable-5-1` and `gpt-6-astra` are both $10 / $50. Use them when a cheaper
   ID fails on your own tasks, not as the everyday planner.

   **Test a tool call before you build on any of these:**

   ```bash
   python scripts/test_tools.py --provider anthropic --model claude-opus-5-5          # dry run, sends nothing
   python scripts/test_tools.py --provider anthropic --model claude-opus-5-5 --send   # needs ANTHROPIC_API_KEY; key never printed
   ```

   OpenRouter and Nous Portal are OpenAI-compatible: use `--provider openai --base-url <gateway>`.
   If a route returns 400 saying tools are unsupported, it can't be your planner, whatever its
   marketing page says.
3. **Web search.** Per §2.2: keyed Firecrawl, or SearXNG plus a keyed extractor. Keyless ring as
   failover only. xAI only with an explicit `web.backend` and the citation caveat in mind.
4. **Memory (unverified).** Prefer a memory-provider plugin (LanceDB, Honcho or Mem0) pointed at a
   local OpenAI-compatible embedding endpoint, so session search stays local even when the planner
   is in the cloud. The `auxiliary: session_search` config block depends on the version; check your
   installed config before wiring it.

---

## 6. Security

Based on the [code-execution](https://hermes-agent.nousresearch.com/docs/user-guide/features/code-execution)
and [security](https://hermes-agent.nousresearch.com/docs/user-guide/security) docs (verified).
This is not a pentest.

**`execute_code` runs as a child process on the agent host, not in a container**, unless you chose
a remote terminal backend. What the docs guarantee:

- **Environment scrubbing.** Variables whose names contain `KEY`, `TOKEN`, `SECRET`, `PASSWORD`,
  `CREDENTIAL`, `PASSWD` or `AUTH` are removed. A small fixed set of `HERMES_*` variables is passed
  through. Anything else has to be allowlisted, and Hermes-managed provider credentials cannot be
  allowlisted back in.
- **Tool whitelist inside scripts.** No recursive `execute_code`, no `delegate_task`, no MCP.
  `terminal()` **is** available (foreground only) and goes through the normal approval path.
- **Limits.** 300 s, 50 KB stdout (full output under `~/.hermes/cache/exec/`), 50 tool calls.
- **Modes.** `code_execution.mode: project` (the default) runs in the session's working directory,
  so a script can `open(".env")`. `strict` uses a temp directory and Hermes's own interpreter.
  Neither mode changes the scrubbing or the whitelist.

What to do:

- Keep `approvals.mode` at `smart` or `manual`. `off`, `hermes --yolo` and `/yolo` disable the
  prompts for dangerous commands. YOLO still respects a hardline blocklist, but that is not a
  sandbox.
- For a research agent that executes code, use the Docker terminal backend and don't mount host
  secrets into it.
- Use `code_execution.mode: strict` unless scripts need to import the project.
- Unattended sessions (cron) default `cron_mode` / `unattended_mode` to `deny` for dangerous
  commands. Leave them at `deny`.

**Treat `web_extract` output as untrusted.** A prompt injection can sit in the visible head or in
the middle the agent pages in later. Don't raise the extract limit to 500,000 characters and then
let the same model both read pages and approve shell commands.

**MCP servers and skills** (`hermes skills install …`, third-party MCP, NotebookLM drivers) are
unpinned code that holds whatever credentials the server or browser has. Pin a git SHA, read the
code, and never point one at a logged-in browser profile you care about. The MCP credential
filtering the docs describe is not a code review.

**SearXNG.** Bind it to localhost unless you mean to run a public metasearch instance.

**Installer.** It is `curl | bash`. Read it first (§1).

---

## 7. Cost

Local isn't free, and hybrid isn't automatically cheaper. No token split has been measured.
Plug in your own electricity rate and card price; the rows below are arithmetic, not quotes.

**Power (upper bound).** The RTX 4090 is rated at 450 W. Real inference draw is lower and was not
measured here. Energy per day = `hours × kW`.

| Assumption (not measured) | Energy | At $0.15/kWh | At $0.30/kWh |
| --- | --- | --- | --- |
| 2 h/day at 450 W (rated maximum) | 0.90 kWh | $0.14 | $0.27 |
| 8 h/day at 300 W (illustrative) | 2.40 kWh | $0.36 | $0.72 |

Card amortisation per day = `purchase_price / (years × 365)`, for example $1,800 over 3 years
≈ $1.64/day. That is a sunk cost, not a per-run cost; don't add it to every research job.

**One heavy planner call: 500K input + 100K output, list price, no cache.**

| Route | Cost |
| --- | --- |
| Hermes 4 405B, $1 / $3 | $0.80 |
| `gemini-3.8-flash` intro rate, $0.75 / $3.75 | $0.75 |
| `claude-sonnet-5` or `gpt-6-sol`, $2 / $10 | $2.00 |
| `claude-opus-5-5`, $4 / $20 | $4.00 |
| `claude-fable-5-1` or `gpt-6-astra`, $10 / $50 | $10.00 |

Ten such calls a day on Opus 5.5 cost $40 before caching. Cache and batch discounts vary by
provider and are not applied above. Hybrid beats all-cloud only if the local tier really absorbs
most of the tokens. Log input, output and cached tokens per job for a week before assuming it does.

---

## 8. Failure modes

| Symptom | Likely cause | How to detect | What to do |
| --- | --- | --- | --- |
| Process killed, or amber "Uses system RAM" | Weights + KV + buffers exceed GPU memory | `nvidia-smi`; runtime badge | Smaller quant, q8_0 KV, shorter window, or a smaller model. Re-run `scripts/kv_cache.py --config` on the file you downloaded. RAM spill is slow, not a fix. |
| ~2 tok/s, GPU idle, RAM busy | Expert weights spilled to system RAM | Low GPU utilisation, high RAM use | Don't use that model for the local tier. |
| Subagents return the same page | Query coalescing plus `~/.hermes/cache/web/` | Identical queries in the log | Vary queries for evals. |
| Synthesis misses the middle of a paper | 15k head+tail extract | `[TRUNCATED]` footer | Page the file on disk, or raise `web.extract_char_limit` and still treat the text as data. |
| Planner returns 400 on tools | Gateway route doesn't accept `tools` | `scripts/test_tools.py --send` exits 1 | Change the ID or the provider. Don't start by debugging prompts. |
| `delegate_task` fails on a batch of 10 | Installed cap is 3 | The tool error names the cap | Read `delegation.max_concurrent_children`. Don't raise depth and width together. |
| Agent runs shell commands from a research script | `execute_code` can call `terminal()` | Approval prompt (none under YOLO) | §6: Docker backend, `strict` mode, approvals on. |
| CUDA "no device" after a kernel upgrade | Arch rolling release, module not rebuilt | `nvidia-smi` fails | §9: DKMS driver, reboot, confirm llama.cpp uses CUDA rather than Vulkan. |

---

## 9. Arch Linux

Per the [Arch wiki NVIDIA page](https://wiki.archlinux.org/title/NVIDIA) (verified). The RTX 4090
is Ada Lovelace, which is supported by `nvidia-open` (stock `linux`), `nvidia-open-lts`,
`nvidia-open-dkms` (any kernel), or the proprietary `nvidia-580xx-dkms` AUR package. Don't install
NVIDIA's `.run` file; it won't upgrade along with the rest of the system.

```bash
# Stock kernel. Use nvidia-open-dkms instead if you are not on the `linux` package.
sudo pacman -S nvidia-open nvidia-utils
nvidia-smi
```

A non-DKMS module breaks after a kernel upgrade until it is rebuilt. If `nvidia-smi` fails, fix
that before touching models.

**llama.cpp.** Hermes's managed runtime downloads its own engine; prefer it unless you need flags
it doesn't expose. Arch's `ggml` package is built with `-DGGML_CUDA=ON`, but a Vulkan backend can
still end up selected. The `llama.cpp-cuda` AUR package has been flagged out of date. Check:

```bash
nvidia-smi   # watch during a short generate; GPU utilisation should rise above 0%
```

If the GPU stays idle, rebuild from [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)
with `-DGGML_CUDA=ON` and confirm the log names CUDA. Put Python clients in a venv, not in the
system interpreter.

---

## 10. Checklist: before you download or subscribe

A TLS error is not a 404. And the Hub never returns 404 to an anonymous request: a missing repo
comes back as **401 `Invalid username or password`**.

- [ ] **Origin up.** `curl -fsSL -o /dev/null -w '%{http_code}\n' https://hermes-agent.nousresearch.com/docs/llms.txt` returns 200. If not, stop.
- [ ] **Hub pins.** `python scripts/check_model_existence.py` (set `HF_TOKEN` if you have one). Exit 0 = pass. Exit 1 = a recommended ID is missing, a known-false ID exists, or a SHA moved off its pin ([`sources.md`](sources.md#hugging-face-pins)); re-read §4 before downloading. A moved SHA means the card changed; it doesn't mean the model was hallucinated. Exit 2 = a lookup didn't complete; retry.
- [ ] **Self-test.** `python -m unittest discover -s tests` passes offline. If it fails, the scripts and this document have drifted apart.
- [ ] **Memory.** `python scripts/kv_cache.py --preset qwen3.8-27b --weights-gb <listed size>`, or `--config <downloaded config.json>`. Then trust the runtime badge over the script.
- [ ] **Catalog badge.** Settings → Providers → Local Models, on your own driver. Green = on-GPU. Amber = slow. Red = pick another model.
- [ ] **Reasoning effort.** The local server is not silently running `xhigh` for extraction legs.
- [ ] **Delegation cap.** Print `delegation.max_concurrent_children`; don't assume 3 or 10.
- [ ] **Planner tool call.** `python scripts/test_tools.py --provider <anthropic|openai|gemini> --model <id> --send` with the key in the environment. Exit 0 = a structured `add(a=2, b=3)` call came back. Exit 1 = the route answered without making that call; a 400 on `tools` rules the candidate out. Exit 2 = the probe didn't complete (no key, 401/403/429/5xx, or a transport error); fix it and rerun, it says nothing about tools.
- [ ] **Prices.** Re-open the vendor pages in §5. Gemini's intro rate ends 2026-12-31.
- [ ] **Approvals.** `approvals.mode` is `smart` or `manual`, YOLO is off, and `code_execution.mode` is `strict` unless you need project imports.
- [ ] **Arch.** `nvidia-smi` works on the current kernel, and a short generate lifts GPU utilisation above zero.
- [ ] **Don't revive** anything on the [known-false list](sources.md#known-false-do-not-reintroduce).
