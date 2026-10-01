# The evaluation ensemble for the final run: members, prices, literature, cost

Written 2026-09-30, re-fetched and revised 2026-10-01; corrected after review 2026-10-01T06:17Z (catalogue, rankings and the endpoint listings of four ids re-read; the DeepSeek first-party price, the Kimi K3 catalogue price, the rankings-API description, the usage and index ranks and the cost tables changed). Every price and catalogue fact below was read from OpenRouter on 2026-10-01 (UTC times given per source); where a value moved since 2026-09-30 the change is stated. Prices change without notice; `elicit --dry-run` must re-read them from `GET https://openrouter.ai/api/v1/models` before the run. Companion files: research/ensemble_members.json (the member table as data, generated from the fetched catalogue) and research/bib/ensemble.bib (the references).

Acronyms: LLM large language model; API application programming interface; JSON JavaScript Object Notation; TTL time to live (how long a cache entry survives); MoE mixture of experts (a sparse model architecture); MoA Mixture-of-Agents (an ensembling scheme, Wang et al. 2024); PoLL Panel of LLM evaluators (Verga et al. 2024); CAPA Chance Adjusted Probabilistic Agreement (a model-similarity metric, Goel et al. 2025); EVPI expected value of perfect information; SE standard error; SD standard deviation.

Terminology follows docs/DESIGN.md section 2: the evaluation ensemble is the set of members (elicitors); each member is an OpenRouter model id with k repeats; the two prompts per scenario are the decision prompt and the instrument prompt.

## 1. Current catalogue

### 1.1 Sources and fetch times

- `GET https://openrouter.ai/api/v1/models` (public, no key), fetched 2026-10-01T05:52:48Z and again at 06:17:39Z, 462 models (464 on 2026-09-30). Fields used: `pricing.prompt`, `pricing.completion`, `pricing.input_cache_read`, `pricing.input_cache_write` (USD per token, multiplied by 1e6 below), `context_length`, `top_provider.max_completion_tokens`, `supported_parameters`, `reasoning` (`mandatory`, `supported_efforts`, `default_effort`), `created`, `canonical_slug`.
- `GET https://openrouter.ai/api/v1/models/{id}/endpoints` for each candidate, fetched 2026-10-01T05:53:52Z; deepseek/deepseek-v4.1-flash, moonshotai/kimi-k3, z-ai/glm-5.3-flash and anthropic/claude-opus-5.5 re-read at 06:17:40Z. Gives the per-provider price, quantisation, uptime and parameter support behind each model id.
- `https://openrouter.ai/rankings`, fetched 2026-10-01T05:52:48Z and again at 06:17:41Z (page state stamped 2026-10-01T05:47:56Z at the first fetch). The page's usage table is fed by `GET https://openrouter.ai/api/frontend/v1/rankings/models?view=week`, fetched 2026-10-01T05:52:48Z and again at 06:17:40Z: 607 rows, exactly one aggregate row per (`model_permaslug`, `variant`) for the seven-day window 2026-09-24 to 2026-09-30 (528 `standard` rows, the rest `free` and other variants); the `date` field is the last day of the window with usage (2026-09-30 for 580 rows) and `rankingMetricValue` is the window total. The page reads "Usage data through Sep 30, 2026". `view=month` (fetched 2026-10-01T05:54Z) covers 2026-09-01 to 2026-09-30 the same way. The page also embeds an intelligence-index panel (`aaData.intelligence`, 106 entries with an `aa_name` and `score` at 06:17:41Z), a benchmark score, not usage.
- Docs pages, fetched as Markdown 2026-10-01T05:52:50Z: `https://openrouter.ai/docs/features/prompt-caching`, `https://openrouter.ai/docs/features/structured-outputs`, `https://openrouter.ai/docs/use-cases/reasoning-tokens`, `https://openrouter.ai/docs/api-reference/parameters`, `https://openrouter.ai/docs/guides/routing/provider-selection`.

### 1.2 The eleven requested ids

All eleven exist under exactly the requested id. Prices are USD per million tokens at the catalogue's top endpoint (`pricing` in `GET /models`), which is usually the cheapest host, not the developer's own endpoint; section 1.2's notes give the first-party price. "json" means `response_format` is in `supported_parameters`; "schema" means `structured_outputs` is. Reasoning column: mandatory?, supported efforts, default. Release is the catalogue `created` date.

| id | released | context | max output | in | out | cache read | cache write | reasoning | json / schema | temperature |
|---|---|---|---|---|---|---|---|---|---|---|
| deepseek/deepseek-v4.1-flash | 2026-09-10 | 1,048,576 | 943,718 | 0.0155 | 0.396 | 0.0029 | none | optional; max/high/low; default high | yes / yes | yes |
| z-ai/glm-5.3-flash | 2026-08-26 | 1,048,576 | 943,717 | 0.15 | 0.50 | 0.03 | none | mandatory; max/high/low; default max | yes / yes | yes |
| z-ai/glm-5.3 | 2026-08-18 | 1,048,576 | 943,718 | 0.30 | 4.40 | 0.24 | none | mandatory; max/high/low; default max | yes / yes | yes |
| anthropic/claude-sonnet-5.5 | 2026-09-28 | 1,000,000 | 128,000 | 2.00 | 10.00 | 0.20 | 2.50 | mandatory; max/xhigh/high/medium/low; default high | yes / yes | yes |
| openai/gpt-5.6-terra | 2026-07-09 | 1,050,000 | 128,000 | 2.00 | 12.00 | 0.20 | 2.50 | optional; max..low, none; default medium | yes / yes | no |
| openai/gpt-6-sol | 2026-09-22 | 1,050,000 | 128,000 | 2.00 | 10.00 | 0.20 | 2.50 | optional; max..low, none; default medium | yes / yes | no |
| openai/gpt-6-luna | 2026-09-22 | 1,050,000 | 128,000 | 0.10 | 0.50 | 0.01 | 0.125 | optional; max..low, none; default medium | yes / yes | no |
| x-ai/grok-4.7 | 2026-09-21 | 500,000 | 450,000 | 2.00 | 6.00 | 0.50 | none | mandatory; xhigh/high/medium/low; default high | yes / yes | yes |
| google/gemini-3.8-flash | 2026-09-02 | 1,048,576 | 65,536 | 0.75 | 3.75 | 0.075 | 0.0417 | mandatory; high/medium/low; default medium | yes / yes | yes |
| qwen/qwen3.8-max-0902 | 2026-09-03 | 1,000,000 | 131,072 | 2.00 | 6.00 | 0.25 | 2.50 | mandatory; xhigh..low, minimal; default xhigh | yes / yes | yes |
| moonshotai/kimi-k3 | 2026-07-16 | 1,048,576 | 943,718 | 0.68 | 10.00 | 0.68 | none | optional; max/high/low; default max | yes / yes | yes |

Changes since 2026-09-30T19:10Z: the catalogue top endpoint for z-ai/glm-5.3 moved from 1.40 in (Z.AI) to 0.30 in (Wafer); for moonshotai/kimi-k3 from 3.00 / 15.00 (Moonshot) to 0.58 / 10.00 (Relace fp4) at 05:52:48Z and 0.68 / 10.00 (same host) at 06:17:39Z; for deepseek/deepseek-v4.1-flash from 0.0198 to 0.0155 in. The eight other rows are unchanged between the three reads. The top-endpoint price is therefore not a stable basis for a cost estimate or a reproducible run; the first-party price is.

Notes from the endpoint listings (2026-10-01T05:53:52Z; DeepSeek, Kimi K3, GLM 5.3 Flash and Opus 5.5 re-read 06:17:40Z):

- deepseek/deepseek-v4.1-flash: 32 endpoints, 0.0155 to 0.60 in, fp4 / fp8 / fp32 / unstated. The catalogue price is OpenInference (fp4). The first-party DeepSeek endpoint is 0.30 / 1.20 with cache read 0.006 (0.02x), lists `response_format` but not `structured_outputs`, max output 393,216, uptime 99.99 percent at fetch. Pin `provider.order: ["deepseek"]` for a reproducible run.
- z-ai/glm-5.3: 39 endpoints, 0.19 to 2.8 in. Z.AI first party (fp8): 1.40 / 4.40, cache read 0.26, `response_format` only, max output 131,072, uptime 99.97 percent. Together and Fireworks serve it at the same price with `structured_outputs`.
- z-ai/glm-5.3-flash: 33 endpoints; Z.AI first party (fp8) 0.15 / 0.50, cache read 0.03, `response_format` only.
- anthropic/claude-sonnet-5.5: eight endpoints (Anthropic, Vertex global, Azure global, Bedrock, Claude on AWS, plus regional variants at 10 percent more). `structured_outputs` is absent on Bedrock and Claude-on-AWS; `temperature` is listed only on Azure. Anthropic first party: 2.00 / 10.00, cache read 0.20, cache write 2.50, uptime 99.99 percent.
- openai/gpt-6-luna, gpt-6-sol, gpt-5.6-terra: OpenAI, Azure, and Flex / Fast tiers; Flex is half price (Luna 0.05 / 0.25; Sol 1.00 / 5.00), Fast double. `temperature` is not a supported parameter on any OpenAI endpoint. All list `response_format` and `structured_outputs`.
- openai/gpt-6.1-sol (released 2026-09-29, not in the request): 2.00 / 10.00 with cache read 0.10; too new for an uptime record on Flex.
- google/gemini-3.8-flash: AI Studio and Vertex, each with flex (0.375 / 1.875), standard (0.75 / 3.75) and priority (1.35 / 6.75). Vertex lists no `temperature`; AI Studio does.
- x-ai/grok-4.7: xAI only (standard, zero-data-retention, priority at 4 / 12); uptime 96.5 to 97.2 percent on the standard and zdr endpoints at fetch.
- qwen/qwen3.8-max-0902: one endpoint (Alibaba), 2.00 / 6.00, cache read 0.25, cache write 2.50, uptime 99.73 percent.
- moonshotai/kimi-k3: 22 endpoints. The catalogue top price (Relace fp4) lists neither `response_format` nor `structured_outputs`, so a request with `require_parameters: true` never lands there. The first-party Moonshot endpoint (mxfp4) is 3.00 / 15.00, cache read 0.30, and lists no `temperature`.

### 1.3 The top 25 by usage and the intelligence index

Usage ranking, view=week, 2026-09-24 to 2026-09-30, `rankingMetricValue` of the model's single aggregate row (equal to prompt plus completion tokens over the window). Basis for every usage rank in this file and in ensemble_members.json: `standard` variants only, ranked by `rankingMetricValue`; free and other variants are dropped (the one free variant inside the raw top 25, nvidia/nemotron-3-ultra-550b-a55b at 6.1 T, would otherwise sit at raw rank 8). Ids with a `-YYYYMMDD` suffix are the catalogue's canonical slugs. Prices from the catalogue (top endpoint).

| rank | model | tokens, week | in the catalogue as |
|---|---|---|---|
| 1 | stealth/space-bunny-alpha | 28.4 T | anonymous, price 0, reasoning mandatory |
| 2 | deepseek/deepseek-v4.1-flash | 22.7 T | candidate |
| 3 | z-ai/glm-5.3-flash | 10.6 T | candidate |
| 4 | xiaomi/mimo-v2.6-flash | 9.1 T | 0.14 / 0.28, no effort control |
| 5 | openai/gpt-5.6-luna | 7.8 T | 0.20 / 1.20 |
| 6 | tencent/hy4-preview | 7.5 T | 0.834 / 2.501, preview |
| 7 | deepseek/deepseek-v4-flash-0731 | 7.0 T | 0.0171 / 1.28, older DeepSeek |
| 8 | openai/gpt-6-luna | 5.1 T | candidate |
| 9 | deepseek/deepseek-v4-flash-0423 | 3.2 T | not in the public models list on 2026-10-01 |
| 10 | typesafe/jev-1.13 | 3.0 T | not in the public models list |
| 11 | z-ai/glm-5.3 | 2.7 T | candidate |
| 12 | tencent/hy3 | 2.4 T | 0.132 / 0.528 |
| 13 | google/gemini-3.8-flash | 2.1 T | candidate |
| 14 | anthropic/claude-opus-5.5 | 1.9 T | 4 / 20 |
| 15 | moonshotai/kimi-k3 | 1.6 T | candidate |
| 16 | openai/gpt-5.6-sol | 1.5 T | 2 / 10 |
| 17 | meta/muse-spark-1.3-contributor | 1.5 T | 0.10 / 0.20 |
| 18 | upstage/solar-pro4 | 1.4 T | 0.09 / 0.36 |
| 19 | anthropic/claude-sonnet-5 | 1.4 T | 2 / 10, predecessor of Sonnet 5.5 |
| 20 | z-ai/glm-5.2 | 1.3 T | 1.40 / 4.40 |
| 21 | minimax/minimax-m3 | 1.3 T | 0.30 / 1.20, no effort control |
| 22 | xiaomi/mimo-v2.6-pro | 1.25 T | 0.435 / 0.87, no effort control |
| 23 | xiaomi/mimo-v2.5 | 1.24 T | 0.14 / 0.28, no effort control |
| 24 | openai/gpt-6-sol | 1.24 T | candidate |
| 25 | openai/gpt-6-astra | 0.91 T | 10 / 50 |

Seven of the eleven requested ids are in this top 25 (DeepSeek V4.1 Flash 2, GLM 5.3 Flash 3, GPT-6 Luna 8, GLM 5.3 11, Gemini 3.8 Flash 13, Kimi K3 15, GPT-6 Sol 24). Claude Sonnet 5.5, released 2026-09-28, is rank 48 for the week with at most three days inside the window; its aggregate row is 251 B tokens and 5.2 M requests. GPT-5.6 Terra is rank 40, Grok 4.7 rank 41, Qwen3.8 Max 0902 rank 51, GPT-6.1 Sol rank 66. The month view (2026-09-01 to 2026-09-30) ranks GLM 5.3 Flash first (56.9 T), then Hy4 preview (56.1 T), DeepSeek V4.1 Flash (51.4 T), GPT-5.6 Luna (51.3 T), DeepSeek V4 Flash 0731 (42.5 T).

Intelligence index embedded in the same page (score; the `aa_name` names the effort setting scored). Rank is the position among all 106 entries sorted by score, ties in array order; entries without a catalogue id (`heuristic_openrouter_slug` null) keep their place and are marked:

| rank | model | score |
|---|---|---|
| 1 | anthropic/claude-opus-5.5 (max effort) | 57.6 |
| 2 | anthropic/claude-sonnet-5.5 (max effort) | 56.0 |
| 3 | anthropic/claude-fable-5.1 (max effort) | 53.4 |
| 4 | qwen/qwen3.8-max | 53.4 |
| 5 | openai/gpt-6-astra (max) | 52.7 |
| 6 | openai/gpt-6.1-sol (max) | 51.8 |
| 7 | anthropic/claude-opus-5 | 50.8 |
| 8 | Claude Fable 5 (max effort; no catalogue id) | 49.6 |
| 9 | openai/gpt-6-sol (max) | 47.5 |
| 10 | openai/gpt-5.6-sol (max) | 47.0 |
| 11 | x-ai/grok-4.7 (xhigh) | 46.4 |
| 13 | qwen/qwen3.8-max-0902 | 45.4 |
| 14 | z-ai/glm-5.3 (max) | 44.8 |
| 16 | moonshotai/kimi-k3 (max) | 43.6 |
| 17 | openai/gpt-5.6-terra (max) | 42.1 |
| 19 | z-ai/glm-5.3-flash | 41.8 |
| 20 | google/gemini-3.8-flash (high) | 40.9 |
| 23 | deepseek/deepseek-v4.1-flash (max effort) | 39.5 |
| 29 | openai/gpt-6-luna (max) | 37.3 |
| 30 | openai/gpt-5.6-luna (max) | 37.3 |

Usage and index disagree: the most used models are the cheapest, the highest-scoring are the most expensive. A member set that wants both must mix tiers. The index is scored at maximum effort; the run will use medium or low effort (section 1.6), so the scores order the candidates but do not predict their behaviour at the run's settings.

### 1.4 Prompt caching per provider (docs, 2026-10-01T05:52:50Z)

Quoted from `https://openrouter.ai/docs/features/prompt-caching`. The page stores its multipliers as constants: Anthropic write 1.25 / read 0.1; Alibaba write 1.25 / read 0.1; DeepSeek read 0.1; Google read 0.25, minimum 4,096 tokens (2.5 Pro) or 1,024 (2.5 Flash); Grok read 0.25; Moonshot read 0.25; Groq read 0.5.

- General: "Most providers automatically enable prompt caching, but note that some (see Alibaba and Anthropic below) require you to enable it on a per-message basis." After a cached request, "provider sticky routing" keeps later requests on the same provider; "Sticky routing is not used when you specify a manual provider order via provider.order"; sticky sessions expire after ten minutes of inactivity; a `session_id` body field or `x-session-id` header pins the routing key and activates stickiness "even before cache usage is observed". Cache activity is reported in `usage.prompt_tokens_details.cached_tokens` and `cache_write_tokens`; `cache_discount` gives the saving.
- OpenAI: "Prompt caching with OpenAI is automated and does not require any additional configuration. There is a minimum prompt size of 1024 tokens." "GPT-5.6 and later charge cache writes at 1.25x the price of the original input pricing, even with automatic caching — no opt-in required." Reads "charged at 0.25x or 0.50x" per the docs; the catalogue shows 0.1x for GPT-6 Luna and Sol (0.01 / 0.10 and 0.20 / 2.00), so the catalogue governs. Explicit `prompt_cache_breakpoint` exists on GPT-5.6 and newer (30-minute minimum TTL). Caching can be switched off per request with `prompt_cache_options.mode: "explicit"` and no breakpoint, because "a prompt of 1024 tokens or more that is only sent once costs more with caching on than off."
- Anthropic: "Cache writes (5-minute TTL): charged at 1.25x", "Cache writes (1-hour TTL): charged at 2x", "Cache reads: charged at 0.1x". Two ways: a top-level `cache_control` field (automatic placement at the last cacheable block) or per-block `cache_control` breakpoints ("There is a limit of four explicit breakpoints"). Minimum cacheable prompt: 4,096 tokens for Opus 4.5 to 4.8 and Haiku 4.5, 1,024 for Sonnet 4.x and Opus 4.x. Sonnet 5.5 is not on the list; verify with `cached_tokens` on the smoke test.
- Google Gemini: "Gemini 2.5 series models and newer support implicit caching", "TTL is on average 3-5 minutes", minimum 1,024 tokens (Flash) or 4,096 (Pro); explicit `cache_control` breakpoints are also accepted, writes "charged at the input token cost plus 5 minutes of cache storage" (catalogue `input_cache_write` 0.0417 for Gemini 3.8 Flash). Docs say reads at 0.25x; the catalogue shows 0.1x (0.075 / 0.75).
- DeepSeek: "automated and does not require any additional configuration"; writes "at the same price as the original input pricing"; reads at 0.1x per docs, 0.02x at DeepSeek's own endpoint per the endpoint listing (0.006 / 0.30).
- Grok (xAI): automatic, writes free, reads 0.25x (catalogue 0.50 / 2.00 agrees).
- Moonshot AI: automatic, writes free, reads 0.25x per docs; catalogue first party 0.30 / 3.00 = 0.1x.
- Z.AI: automatic; "Cache writes: no cost (Z.AI currently lists cached input storage as limited-time free)"; reads "typically about 0.2x" (first party 0.26 / 1.40 = 0.19x); "OpenRouter sends Z.AI a session affinity key with each request, derived from your account and, when provided, your session_id."
- Alibaba Qwen: "Alibaba prompt caching requires explicit cache breakpoints. Add cache_control: { "type": "ephemeral" } ... Cache writes use a 5-minute TTL." Listed for `qwen/qwen3-max`, `qwen/qwen-plus`, `qwen/qwen3.6-plus`, `qwen/qwen3-coder-plus`, `qwen/qwen3-coder-flash` and `deepseek/deepseek-v3.2`; "Snapshot endpoints ... do not support explicit caching." qwen3.8-max-0902 is a snapshot and is not listed, although the catalogue shows a cache-read price for it.

Consequence for the harness (docs/DESIGN.md section 4 says the shared prefix comes first and the request marks it with a `cache_control` breakpoint): one breakpoint on the prefix block is correct for Anthropic and harmless elsewhere (the docs say a block marked with `cache_control` "gets a prompt_cache_breakpoint when routed to a supporting OpenAI model", Google accepts it, the others ignore it). The calls that share a prefix (same scenario, same member: decision, instrument, perspective ablation, times k) must run within five minutes of each other for the Anthropic and Google caches to hit, so the elicitation loop should iterate scenario, then member, then prompt, then repeat. With `provider.order` set (section 3.3) sticky routing is off, which is fine: the order already fixes the provider.

### 1.5 JSON output per provider (docs, 2026-10-01T05:52:50Z)

- `https://openrouter.ai/docs/api-reference/parameters`: "Setting to { "type": "json_object" } enables JSON mode, which guarantees the message the model generates is valid JSON. Note: when using JSON mode, you should also instruct the model to produce JSON yourself via a system or user message."
- `https://openrouter.ai/docs/features/structured-outputs`: `response_format.type: json_schema` with `strict: true`. "Support is determined per endpoint, not just per model: the same model may be served by multiple providers, and only some of those providers may support structured outputs." "Set require_parameters: true in your provider preferences" to route only to endpoints that support every parameter sent. "Enforcement varies by provider: some guarantee schema-conforming output, while others translate your schema into their own structured-output format or treat it as a strong hint, so exact compliance is not guaranteed on every endpoint."
- `https://openrouter.ai/docs/guides/routing/provider-selection`: "When you set require_parameters to true, the request won't even be routed to that provider." Even without it, "`response_format` (including structured outputs)" is a soft preference: "If some of a model's providers support one of these parameters and others don't, the request is only routed to the supporting providers."
- Per model (catalogue `supported_parameters`): all eleven requested ids list both `response_format` and `structured_outputs`. Per endpoint, the first-party DeepSeek and Z.AI endpoints, Anthropic on Bedrock and Claude-on-AWS list `response_format` only; the Relace host of Kimi K3 lists neither.

Decision: keep the template's own JSON instruction and the validator (docs/DESIGN.md section 4), send `response_format: {"type": "json_object"}` as the common denominator, and send `provider: {"require_parameters": true}` so a request never lands on an endpoint that ignores it. Strict `json_schema` is a per-endpoint gamble, is absent from two of the six first-party endpoints we want to pin, and adds nothing our validator does not already check.

### 1.6 Reasoning tokens (docs, 2026-10-01T05:52:50Z)

Quoted from `https://openrouter.ai/docs/use-cases/reasoning-tokens`:

- "Reasoning tokens are considered output tokens and charged accordingly. On most providers they also count against the request's max_tokens." "If the limit is small enough that the model spends all of it reasoning, the response returns finish_reason: "length" with an empty content, and the reasoning tokens are still billed." Detection: "subtract usage.completion_tokens_details.reasoning_tokens from usage.completion_tokens."
- `reasoning.effort`: max and xhigh about 95 percent of `max_tokens`, high 80, medium 50, low 20, minimal 10, none disables. `reasoning.max_tokens` sets the budget directly where the catalogue's `reasoning.supports_max_tokens` is true; that flag is absent from every one of the eleven candidates' `reasoning` objects, so effort is the control to use. `reasoning.exclude: true` hides the trace but "The tokens are still billed".
- Anthropic: "budget_tokens = max(min(max_tokens * effort_ratio, 128000), 1024)"; "max_tokens must be strictly higher than the reasoning budget". Summarised thinking is the default display and "The model consumes the same number of tokens either way".
- Gemini 3: effort maps to `thinkingLevel` (xhigh maps down to high); "the actual number of reasoning tokens consumed is determined internally by Google. There are no publicly documented token limit breakpoints for each level."
- OpenAI and Grok: effort levels only. `reasoning.mode: "pro"` exists for GPT-5.6 and newer on OpenAI and Azure; "Pro mode bills at the same per-token rates as standard mode, but typically consumes more tokens." Do not use it.
- Catalogue `reasoning.mandatory: true` means `effort: "none"` is rejected. Four of the six recommended members have mandatory reasoning; only GPT-6 Luna and DeepSeek V4.1 Flash can switch it off.

Consequence for voi_rank/providers/openrouter.py (read 2026-10-01): it sends `max_tokens: 4000`, `temperature: 1.0` and no `reasoning` object. With mandatory-reasoning members that is a truncation trap: Sonnet 5.5 at its default high effort gets a 3,200-token thinking budget out of 4,000 and 800 tokens for a JSON answer that the pilot shows needs about 1,100 (section 4). `temperature` is not a supported parameter on any OpenAI endpoint, so with `require_parameters: true` a request carrying it finds no endpoint. Recommended request shape, per member, set in the protocol file: `max_tokens: 16000`; `reasoning: {"effort": E}` with E = medium for OpenAI, Anthropic, Google and Grok and E = low for DeepSeek and GLM (whose effort levels are max/high/low); no `temperature` for OpenAI members; record `usage.completion_tokens_details.reasoning_tokens` per call. Measure the actual output length per member on the designated smoke test (five scenarios, k = 1) before fixing E for the run.

## 2. Literature

The question has three parts: (a) does a diverse ensemble of cheaper models beat one strong model on judgment and forecasting tasks; (b) repeated sampling of one model against diversity across models; (c) correlated errors between models of one developer. Every source below was fetched on 2026-09-30 and re-fetched on 2026-10-01 (arXiv metadata via `https://export.arxiv.org/api/query` at 05:53:55Z, HTML full texts at `https://arxiv.org/html/<id><version>` at 05:54:42Z, DOI records via `https://api.crossref.org/works/<doi>` at 05:52:53Z); every number quoted below was located in the full text on 2026-10-01.

### 2.1 Ensembles of LLM forecasters against human crowds

Schoenegger, Tuminauskaite, Park and Tetlock 2024, "Wisdom of the Silicon Crowd", arXiv 2402.19379 (v6). "a crowd of twelve LLMs" from companies in six countries forecast 31 binary questions against "925 human forecasters" on Metaculus (October 2023 to January 2024). Result: "the LLM crowd, M=0.20 (SD=0.12), being significantly more accurate than the benchmark, t(30) = -2.35, p = 0.026" (the benchmark is the 0.25 Brier score of always saying 50 percent), and "we fail to find statistically significant differences between the LLM crowd's mean Brier score of M=0.20 (SD=0.12) and that of the human crowd, M=0.19 (SD=0.19), t(60) = 0.19, p = 0.850." The adjusted p-values after multiple-comparison correction are 0.039, 0.850 and 0.006 for the three preregistered hypotheses. Two details matter for us. First, the paper's Table 2 ("Average Brier Score for Each Model") gives members from GPT-4 at 0.15 to Coral (Command) at 0.38, with GPT3.5-Turbo-Instruct and Llama-2-70B at 0.25 and the human crowd at 0.19; the median-aggregated crowd (0.20) did not beat its best member. Second, "an acquiescence effect, with mean model predictions being significantly above 50%, despite an almost even split of positive and negative resolutions" ("just over 45% of questions resolving positively"): a shared bias that aggregation cannot remove.

Schoenegger and Park 2023, arXiv 2310.13014: a single frontier model in a real tournament. "We observe an average Brier score for GPT-4's predictions of B=.20 (SD=.18), while the human forecaster average Brier score was B=.07 (SD=.08)", and "GPT-4's forecasts did not significantly differ from the no-information forecasting strategy of assigning a 50% probability to every question." This is the baseline the 2024 ensemble paper improves on.

Halawi, Zhang, Yueh-Han and Steinhardt 2024, "Approaching Human-Level Forecasting with Language Models", arXiv 2402.18563. Fourteen instruction-tuned models evaluated zero-shot; "Only the GPT-4 and Claude-2 series beat the unskilled baseline by a large margin (>.02). Moreover, while GPT-4-1106-Preview achieves the lowest Brier score of .208, it trails significantly behind the human crowd performance of .149." Their Table 7 gives GPT-4-1106-Preview 0.208 zero-shot and 0.209 with a scratchpad, Llama-2-13B 0.226 and 0.268, Mistral-8x7B 0.238 and 0.238, against the random baseline 0.250. Their full system (retrieval, fine-tuned reasoning, three base and three fine-tuned forecasts aggregated by trimmed mean, "as this performs best on the validation set among the ensemble methods we implement") reaches 0.179 on all questions against the crowd's 0.149, and beats the crowd on selected subsets.

Karger et al. 2024, "ForecastBench", arXiv 2409.19839 (v5). "superforecasters achieve an overall mean Brier score of 0.096, significantly outperforming both the general public (Brier = 0.121, p<0.001) and the top LLM performer on the 200-item subset (Claude 3.5 Sonnet: Brier = 0.122, p<0.001)." "The top-performing LLMs all had access to the crowd forecast on market questions." They also build an LLM ensemble from "3 models (GPT-4o, Claude-3.5-Sonnet, and Gemini-1.5-Pro) and 3 prompts crafted by superforecasters", aggregated by median, geometric mean and geometric mean of log odds, because "Metaculus (2023) shows that an ensemble of all forecasters consistently outperforms using just the top 5, 10, ..., 30 best forecasters (based on past scores)."

Reading for our purpose: an LLM crowd reaches the level of a human crowd on binary forecasts; no single model did in these three studies; the crowd's gain comes from cancelling idiosyncratic error, and it does not remove biases the members share.

### 2.2 Panels of cheaper members against one strong model

Verga et al. 2024, "Replacing Judges with Juries", arXiv 2404.18796 (v2). "We construct a PoLL from three models being drawn from three disparate model families (Command R, Haiku, and GPT-3.5)." Result: "using a PoLL composed of a larger number of smaller models outperforms a single large judge, exhibits less intra-model bias due to its composition of disjoint model families, and does so while being over seven times less expensive." Cost: "the cost of running our specific instance of PoLL is $1.25/input per million tokens + $4.25/output, whereas the cost of running GPT-4 Turbo is $10/input + $30/output." They also report that "In some scenarios, GPT-4 is a relatively weak judge, exhibiting high variance with minor changes to the prompt" and that "Intra-model scoring bias is reduced by pooling judgements across a panel of heterogeneous evaluator models".

Wang et al. 2024, "Mixture-of-Agents", arXiv 2406.04692. Six open models from five developers in layers, "achieving a score of 65.1% compared to 57.5% by GPT-4 Omni" on AlpacaEval 2.0 (length-controlled win rate; MoA-Lite 59.3, MoA with GPT-4o as aggregator 65.7). They name "the collaborativeness of LLMs — wherein an LLM tends to generate better responses when presented with outputs from other models, even if these other models are less capable by itself."

Li, Lin, Xia and Jin 2025, "Rethinking Mixture-of-Agents", arXiv 2502.00674. The direct rebuttal: "Self-MoA achieves 6.6% improvement over MoA on the AlpacaEval 2.0 benchmark, and an average of 3.8% improvement across various benchmarks, including MMLU, CRUX, and MATH." "We confirm that the MoA performance is rather sensitive to the quality, and mixing different LLMs often lowers the average quality of the models." When does mixing win? "Mixed-MoA generally exhibits greater diversity than Self-MoA, which can lead to improved performance when the model quality is similar. This advantage arises when individual models achieve similar overall performance while maintaining significant cross-model diversity." On their mixture task (Table 6) the best mixed panels scored 59.86 and 60.04 against 59.69 for the best single model repeated six times, "improves upon Self-MoA of dddddd by 0.17% and 0.35%".

### 2.3 Repeated sampling of one model

Wang et al. 2022, "Self-Consistency", arXiv 2203.11171 (v4): sampling several reasoning paths and taking the majority answer "boosts the performance of chain-of-thought prompting with a striking margin on a range of popular arithmetic and commonsense reasoning benchmarks, including GSM8K (+17.9%), SVAMP (+11.0%), AQuA (+12.2%), StrategyQA (+6.4%) and ARC-challenge (+3.9%)."

Li et al. 2024, "More Agents Is All You Need", arXiv 2402.05120 (v2): "When the ensemble size scales up to 15, Llama2-13B achieves comparable accuracy with Llama2-70B" and "the enhanced Llama2-13B model achieves 59% accuracy on the GSM8K dataset, outperforming the Llama2-70B model, which scores 54%" (Table 2: Llama2-13B single 0.35, ensemble 0.59; Llama2-70B single 0.54). "the degree of enhancement is correlated to the task difficulty."

Brown et al. 2024, "Large Language Monkeys", arXiv 2407.21787 (v3): "coverage – the fraction of problems that are solved by any generated sample – scales with the number of samples over four orders of magnitude" and "the fraction of issues solved with DeepSeek-Coder-V2-Instruct increases from 15.9% with one sample to 56% with 250 samples". The caveat that applies to us: "In domains without automatic verifiers, we find that common methods for picking from a sample collection (majority voting and reward models) plateau beyond several hundred samples and fail to fully scale with the sample budget." Elicited probabilities and costs have no verifier.

Chen et al. 2024, "Are More LLM Calls All You Need?", arXiv 2403.02419 (v2): "the performance of both Vote and Filter-Vote can first increase but then decrease as a function of the number of LM calls" because "more LM calls lead to higher performance on 'easy' queries, but lower performance on 'hard' queries, and non-monotone behavior can emerge when a task contains both types of queries." Repeats sharpen whatever the model already believes; on a question the model gets systematically wrong, more repeats make the wrong answer more confident.

### 2.4 Correlated errors across models and developers

Kim, Garg, Peng and Garg 2025, "Correlated Errors in Large Language Models", arXiv 2506.07962. Data: "Responses of 349 LLMs on 12,032 multiple choice questions on a HuggingFace leaderboard, 71 LLMs on 14,042 multiple choice questions on the Helm leaderboard, and 20 LLMs on 1,800 resume-job description pairs." Result: "on Helm, pairs of models agree on average about 60% of the time when both models are incorrect (choosing between incorrect answers uniformly at random would lead to an agreement rate of 1/3)." Drivers: "models with the same provider (company), with the same base architecture, or with similar sizes have more correlated errors. Importantly, even after conditioning on these factors, pairs of models that are more accurate individually also have more correlated errors." Downstream: "judges overinflate the accuracy of models that are less accurate than it—especially for models of the same provider or architecture."

Goel et al. 2025, "Great Models Think Alike and this Undermines AI Oversight", arXiv 2502.04313 (v2). With the CAPA similarity metric: "We find a significant (p<0.01) positive correlation (average Pearson r= 0.84) between LLM-as-a-judge scores and model similarity (κp) for all judges", and their section 5 is titled "Models are making more similar mistakes as capabilities increase".

Zhou, Xiong, Savarese and Wu 2024, "Shared Imagination: LLMs Hallucinate Alike", arXiv 2407.16604: "On 13 LLMs from four model families (GPT, Claude, Mistral, and Llama 3), models achieve an average 54% correctness rate on directly generated questions (with random chance being 25%), with higher accuracy when the AM is the same, or in the same model family, as the QM." Models answer each other's invented questions the same way, and same-family pairs agree most.

### 2.5 The classical results the above rediscover

Clemen and Winkler 1985, Operations Research 33(2) 427-442, DOI 10.1287/opre.33.2.427 (abstract via Crossref, 2026-10-01T05:52:53Z): "positive dependence among information sources can have a serious detrimental effect on the precision and value of the information". The arithmetic behind it, for n sources with equal error variance sigma^2 and pairwise error correlation rho: Var(mean) = sigma^2 [(1 - rho)/n + rho], so the number of independent sources the panel is worth is n_eff = n / (1 + (n - 1) rho), which is at most 1/rho however large n grows. Six members at rho = 0.5 are worth 1.7 independent ones (limit 2.0); at rho = 0.2 they are worth 3.0 (limit 5.0); at rho = 0.8 they are worth 1.2. Kim et al. say same-developer pairs sit at the high end of rho; that is the whole argument for spanning developers.

Hong and Page 2004, PNAS 101(46) 16385-16389, DOI 10.1073/pnas.0403723101 (abstract via Crossref, 2026-10-01T05:52:53Z): "when selecting a problem-solving team from a diverse population of intelligent agents, a team of randomly selected agents outperforms a team comprised of the best-performing agents. This result relies on the intuition that, as the initial pool of problem solvers becomes large, the best-performing agents necessarily become similar in the space of problem solvers." Goel et al. 2025 report exactly this convergence among frontier models.

Clemen 1989, International Journal of Forecasting 5(4) 559-583, DOI 10.1016/0169-2070(89)90012-5, is the standard review of forecast combination (record via Crossref, 2026-10-01; no abstract is served, so nothing beyond the title is claimed here).

## 3. Recommendation

### 3.1 What the elicitation needs from the ensemble

The members fill eight numbers per scenario (p, B, K on the decision prompt; s, t, C_build, C_run, n on the instrument prompt) as three percentiles each, fitted to Beta or lognormal distributions and pooled as an equal-weight mixture (docs/DESIGN.md sections 4 and 6). Nobody knows the true values, so there is no verifier and no majority vote; what the pool gives is a central estimate (the pooled median) and a spread. Two kinds of noise enter the pooled median: repeat noise (the same member, asked again) and member spread (different members' central beliefs). The pilot data measure both. From studies/ai-safety-evals/voi.db, protocol p003 (read 2026-10-01: 15 scenarios, three claude_cli members haiku, sonnet, opus, k = 5, 225 valid of 229 elicitations, binary template), take the elicited median of each parameter on the logit scale (p, s, t) or log scale (B, K, C). Per scenario cell: sigma_w^2 is the mean over members of the sample variance across the five repeats; the variance of the three member means minus sigma_w^2 / 5 is the between-member component sigma_b^2. Averaged over the 15 cells:

| parameter | sigma_w (repeats) | sigma_b (members) | ratio sigma_b^2 / sigma_w^2 |
|---|---|---|---|
| p | 0.47 | 0.54 | 1.29 |
| s | 0.28 | 0.25 | 0.83 |
| t | 0.35 | 0.44 | 1.54 |
| B (log) | 0.94 | 0.90 | 0.92 |
| K (log) | 0.95 | 0.83 | 0.77 |
| C (log) | 0.54 | 0.55 | 1.02 |

Three lessons. For the prior p and the specificity t, members disagree more than a member disagrees with itself; for s and the dollar quantities the two are about equal. A single call on a dollar quantity is noisy by a factor of about e (one log unit, sigma_w near 0.95), so no single elicitation is a usable estimate; only the pool is. And the pilot's three members were all one developer, so the sigma_b row is a lower bound on what a multi-developer panel will show (Kim et al. 2025).

With m members and k repeats and no shared-developer term, Var(pooled mean) = sigma_b^2 / m + sigma_w^2 / (m k). Using the pilot values: for p, going from (m = 6, k = 1) to (6, 3) cuts the SE by 16 percent for three times the calls; going to (12, 1) cuts it by 29 percent for twice the calls. For B the same moves give 19 and 29 percent; for t, 14 and 29. Members beat repeats per call whenever sigma_b is not far below sigma_w, which holds for every parameter here. The constraint is the catalogue: past six developers the candidates are previews, anonymous models or models without effort control (section 1.3). So m is capped near six, and k is set by two measurement needs rather than by variance: k >= 2 is the minimum that lets figure F9 (cross-member agreement) compare between-member spread with within-member spread, and k = 3 gives that within-member estimate two degrees of freedom instead of one. The cost difference between k = 2 and k = 3 is about USD 19 at N = 60 (section 4).

### 3.2 The members

Six members, six developers, three price tiers, all with `response_format` and a controllable reasoning setting, all with a first-party endpoint. Prices USD per million tokens at the first-party endpoint (endpoint listings 2026-10-01T05:53:52Z, DeepSeek re-read 06:17:40Z), which is what the run pins. Index: score (rank among the 106 entries, section 1.3). Usage rank: week view, standard variants only (section 1.3):

| member | developer | in / out | cache read | index | usage rank | why |
|---|---|---|---|---|---|---|
| anthropic/claude-sonnet-5.5 | Anthropic | 2.00 / 10.00 | 0.20 | 56.0 (2) | 48, at most three days in the window | highest-scoring member; continuity with the iteration runs (claude_cli sonnet); the one member whose caching needs a breakpoint |
| openai/gpt-6-luna | OpenAI | 0.10 / 0.50 | 0.01 | 37.3 (29) | 8 | the OpenAI tier at a twentieth of Sonnet's price; reasoning switchable; GPT-6 Sol (47.5) is the upgrade if the smoke test shows Luna's validity rate below the others |
| google/gemini-3.8-flash | Google | 0.75 / 3.75 | 0.075 | 40.9 (20) | 13 | Google's current Flash; implicit caching |
| deepseek/deepseek-v4.1-flash | DeepSeek | 0.30 / 1.20 | 0.006 | 39.5 (23) | 2 | the most used paid model on the platform; open weights; a new architecture (catalogue description: sparse MoE on a Causal Encoder-Decoder), the most different training lineage in the set |
| z-ai/glm-5.3 | Z.ai | 1.40 / 4.40 | 0.26 | 44.8 (14) | 11 | open weights; the full model rather than Flash because Li et al. 2025 show quality dominates diversity once quality differs |
| x-ai/grok-4.7 | xAI | 2.00 / 6.00 | 0.50 | 46.4 (11) | 41 | sixth developer with a distinct data lineage; the second-highest index score in the set |

Alternates, in order: qwen/qwen3.8-max-0902 (index 45.4; single Alibaba endpoint; default effort xhigh; no documented caching for this snapshot), openai/gpt-6-sol (index 47.5, Sonnet's price, the quality upgrade for the OpenAI slot), moonshotai/kimi-k3 (index 43.6; 3.00 / 15.00 first party, the most expensive candidate), z-ai/glm-5.3-flash (index 41.8; if the budget must stay under USD 20), openai/gpt-6.1-sol (index 51.8, released 2026-09-29, too new for an uptime record). If a seventh member is wanted, take Qwen3.8 Max 0902: it adds the strongest non-US candidate at USD 0.027 per central call (USD 14.58 at N = 60, k = 3).

Excluded on purpose: stealth/space-bunny-alpha (anonymous, unpriced, not reproducible), tencent/hy4-preview (preview, 92.7 percent uptime on the first-party endpoint at fetch), the Xiaomi MiMo and MiniMax models (no effort control), openai/gpt-5.6-terra and gpt-5.6-luna (superseded tiers, same or lower index at a higher price than their GPT-6 successors), and any second model from a developer already in the set (Kim et al. 2025).

Repeats: k = 3. Prompts per scenario: decision, instrument, and the developer-perspective ablation of the decision prompt, so three calls per scenario per member per repeat.

### 3.3 Request settings per member

- `max_tokens: 16000` for every member (reasoning counts against it; the pilot's visible answer is about 1,100 tokens, and reasoning at medium effort is expected at 1,000 to 3,000; section 4).
- `reasoning.effort`: medium for Sonnet 5.5, GPT-6 Luna, Gemini 3.8 Flash and Grok 4.7; low for DeepSeek V4.1 Flash and GLM 5.3 (their effort levels are max/high/low, so "medium" would be mapped to a neighbour anyway). Never `mode: "pro"`. Do not use `reasoning.max_tokens`: no candidate's catalogue entry flags `supports_max_tokens`.
- `response_format: {"type": "json_object"}` plus `provider: {"require_parameters": true}`; keep the template's JSON instruction and the validator.
- No `temperature` for OpenAI members (unsupported on every OpenAI endpoint). For the others keep the harness default; a temperature of 1.0 is what makes repeats informative.
- One `cache_control: {"type": "ephemeral"}` breakpoint on the shared prefix block; loop order scenario, member, prompt, repeat so the nine calls of a scenario-member land inside the five-minute TTL. Read `usage.prompt_tokens_details.cached_tokens` on the smoke test to confirm hits per member.
- Pin the first-party endpoint for every member with `provider.order` (`["anthropic"]`, `["openai"]`, `["google-ai-studio"]`, `["deepseek"]`, `["z-ai"]`, `["xai"]`) and `allow_fallbacks: false`, and record `provider` from the response. The reason is section 1.2: the cheapest host of GLM 5.3 and Kimi K3 changed overnight, and the third-party hosts differ in quantisation (fp4 to fp32). A run that mixes hosts across repeats is not reproducible; a run that fails over to a different host on an outage is at least recorded. If the harness must keep fallbacks, set `provider.quantizations` instead.
- Store `usage` (including `completion_tokens_details.reasoning_tokens` and `cost`) per call; the harness already stores the raw body.

## 4. Cost table

Formula: calls = N scenarios x 3 prompts (decision, instrument, perspective ablation of the decision prompt) x m members x k repeats; cost = sum over members of calls_per_member x (P x price_in + O x price_out) / 1e6, with P prompt tokens and O output tokens including reasoning. Token cases: low P = 4,000, O = 1,500; central P = 6,000, O = 2,500; high P = 8,000, O = 4,000; stress P = 6,000, O = 8,000.

Calibration against the pilot (studies/ai-safety-evals, protocol p003, read 2026-10-01). Prompt side: the elicitor template is 848 words (5,203 characters, about 1,300 tokens) and a scenario record is 3,064 characters at the median (about 770 tokens), so the present prompt is about 2,100 tokens; a 300 to 600 word curated context adds 400 to 800, and the `abstracts` context mode more, so 4,000 to 8,000 covers the modes. Output side, per member, median (p10 to p90) of `usage.output_tokens` including thinking: haiku 10,844 (7,624 to 16,951; thinking 9,657), sonnet 4,158 (3,357 to 5,355; thinking 2,613), opus 1,165 (1,059 to 1,276; the CLI ran opus without extended thinking). The visible answer was 4,314 (haiku), 4,363 (sonnet) and 3,225 (opus) characters at the median, about 800 to 1,100 tokens. The stress row (O = 8,000) is therefore the haiku-like case at the CLI's own thinking settings; the central row (O = 2,500) is the sonnet-like case with reasoning held near 1,400 tokens by the effort settings of section 3.3. The pilot's own bill was USD 14.86 for 225 valid calls at claude_cli prices, each call also reading a cached system context that OpenRouter calls will not carry (`usage.cache_read_input_tokens` over the 225 valid calls: median 88,510, range 0 to 173,198, 49 distinct values).

Per call, uncached, USD, first-party prices (endpoint listings 2026-10-01T05:53:52Z, DeepSeek re-read 06:17:40Z):

| member | in $/M | out $/M | low | central | high | stress |
|---|---|---|---|---|---|---|
| anthropic/claude-sonnet-5.5 | 2.00 | 10.00 | 0.0230 | 0.0370 | 0.0560 | 0.0920 |
| openai/gpt-6-luna | 0.10 | 0.50 | 0.0011 | 0.0019 | 0.0028 | 0.0046 |
| google/gemini-3.8-flash | 0.75 | 3.75 | 0.0086 | 0.0139 | 0.0210 | 0.0345 |
| deepseek/deepseek-v4.1-flash | 0.30 | 1.20 | 0.0030 | 0.0048 | 0.0072 | 0.0114 |
| z-ai/glm-5.3 | 1.40 | 4.40 | 0.0122 | 0.0194 | 0.0288 | 0.0436 |
| x-ai/grok-4.7 | 2.00 | 6.00 | 0.0170 | 0.0270 | 0.0400 | 0.0600 |
| six members together | | | 0.0650 | 0.1039 | 0.1558 | 0.2461 |

Total, six members, three prompts per scenario, uncached, first-party prices, USD:

| N | k | calls | low | central | high | stress |
|---|---|---|---|---|---|---|
| 30 | 1 | 540 | 6 | 9 | 14 | 22 |
| 30 | 2 | 1,080 | 12 | 19 | 28 | 44 |
| 30 | 3 | 1,620 | 17 | 28 | 42 | 66 |
| 42 | 1 | 756 | 8 | 13 | 20 | 31 |
| 42 | 2 | 1,512 | 16 | 26 | 39 | 62 |
| 42 | 3 | 2,268 | 25 | 39 | 59 | 93 |
| 60 | 1 | 1,080 | 12 | 19 | 28 | 44 |
| 60 | 2 | 2,160 | 23 | 37 | 56 | 89 |
| 60 | 3 | 3,240 | 35 | 56 | 84 | 133 |

At the catalogue's top-endpoint prices of 2026-10-01 (DeepSeek 0.0155 / 0.396, GLM 5.3 0.30 / 4.40, others equal) the same table reads 5 / 8 / 13 / 21 at (30, 1) and 31 / 51 / 76 / 125 at (60, 3): the cheapest hosts save USD 6 at the central case, not enough to give up a pinned endpoint for.

Per member, central case, uncached, first-party prices, USD (N x 3 x k calls per member):

| member | 30,1 | 30,2 | 30,3 | 42,1 | 42,2 | 42,3 | 60,1 | 60,2 | 60,3 |
|---|---|---|---|---|---|---|---|---|---|
| anthropic/claude-sonnet-5.5 | 3.33 | 6.66 | 9.99 | 4.66 | 9.32 | 13.99 | 6.66 | 13.32 | 19.98 |
| openai/gpt-6-luna | 0.17 | 0.33 | 0.50 | 0.23 | 0.47 | 0.70 | 0.33 | 0.67 | 1.00 |
| google/gemini-3.8-flash | 1.25 | 2.50 | 3.75 | 1.75 | 3.50 | 5.24 | 2.50 | 5.00 | 7.49 |
| deepseek/deepseek-v4.1-flash | 0.43 | 0.86 | 1.30 | 0.60 | 1.21 | 1.81 | 0.86 | 1.73 | 2.59 |
| z-ai/glm-5.3 | 1.75 | 3.49 | 5.24 | 2.44 | 4.89 | 7.33 | 3.49 | 6.98 | 10.48 |
| x-ai/grok-4.7 | 2.43 | 4.86 | 7.29 | 3.40 | 6.80 | 10.21 | 4.86 | 9.72 | 14.58 |

Caching: assume 80 percent of P is the shared prefix (scenario, context, system prompt), the first call of each scenario-member writes it and the other 3k - 1 calls read it, at the first-party write and read multipliers. Central case, N = 60, USD per member:

| member | write x | read x | k=1 uncached | k=1 cached | k=3 uncached | k=3 cached |
|---|---|---|---|---|---|---|
| anthropic/claude-sonnet-5.5 | 1.25 | 0.10 | 6.66 | 5.77 | 19.98 | 15.98 |
| openai/gpt-6-luna | 1.25 | 0.10 | 0.33 | 0.29 | 1.00 | 0.80 |
| google/gemini-3.8-flash | 0.06 | 0.10 | 2.50 | 1.90 | 7.49 | 5.73 |
| deepseek/deepseek-v4.1-flash | 1.00 | 0.02 | 0.86 | 0.69 | 2.59 | 1.91 |
| z-ai/glm-5.3 | 1.00 | 0.19 | 3.49 | 2.84 | 10.48 | 7.85 |
| x-ai/grok-4.7 | 1.00 | 0.25 | 4.86 | 4.00 | 14.58 | 11.12 |

Caching saves about a quarter of the total (USD 56 to 43 at N = 60, k = 3), because output tokens at five times the input price dominate the bill. Budget the uncached number and treat the saving as slack. The recommended run (N = 60, k = 3) is USD 56 central, USD 84 high, USD 133 if reasoning runs unchecked; add the same again for a retry allowance and the smoke test, so a USD 150 to 250 key limit covers it.

Counterfactual, same call count from one strong model (N = 60, three prompts, 18 calls per scenario-prompt to match six members x k = 3, central tokens): Claude Opus 5.5 (4 / 20) USD 240; GPT-6 Astra (10 / 50) USD 599; Claude Sonnet 5.5 or GPT-6 Sol alone USD 120. At k = 3 alone: Opus 5.5 USD 40, Astra USD 100, Sonnet 5.5 or GPT-6 Sol USD 20, Qwen3.8 Max 0902 USD 15, Kimi K3 (first party) USD 30.

## 5. The counter-argument: fewer, stronger models

The case. Li et al. 2025 show that six repeats of the best model beat a mix of six different models by 6.6 points on AlpacaEval 2.0 and by 3.8 percent across MMLU, CRUX and MATH, and that "mixing different LLMs often lowers the average quality of the models." Halawi et al. 2024 found no base model within 0.06 Brier of the crowd and their system's gain came from retrieval and fine-tuning, not from mixing weak models with GPT-4. In Schoenegger et al. 2024 the twelve-model median (0.20) was worse than its best member (GPT-4, about 0.15). Kim et al. 2025 and Goel et al. 2025 show that the most accurate models make the most similar mistakes even across developers, so the diversity bought by spanning developers shrinks exactly among the models one would want. The intelligence index (section 1.3) puts Sonnet 5.5 at 56.0 and the cheapest recommended member, GPT-6 Luna, at 37.3. On this reading, the ensemble spends its budget on members that pull the pooled median toward mediocrity, and Claude Opus 5.5 at k = 3 (USD 40 at N = 60) would give a cleaner central estimate than six models at k = 3 (USD 56).

Where it is right. Quality is not optional: a member that cannot follow the JSON contract, cannot reason about a cost scale, or refuses half the scenarios adds noise and refusal rows, not information. That is why the recommendation takes GLM 5.3 rather than GLM 5.3 Flash, Sonnet 5.5 rather than Haiku 4.5, keeps GPT-6 Sol as the named upgrade for the OpenAI slot, and excludes the anonymous rank-1 model, the preview models and the models with no effort control. It is also why the pool is an equal-weight mixture only over valid elicitations, with validation and one retry per call, and why the smoke test measures validity rate per member before the run.

Where it fails for this study, and why the evidence favours the ensemble.

1. There is no verifier and no leaderboard for our quantity. Self-MoA needs to know which model is best; AlpacaEval and MATH tell it. Nobody knows which model elicits the better prior on a virology test's decision-changing power, and the index scores a different task at a different effort setting. Hong and Page's condition for the best-performers team to lose is that the pool is large and the best become similar; Goel et al. 2025 report that similarity among frontier models is rising.
2. The failure mode we fear is shared bias, not variance. Schoenegger et al.'s acquiescence effect, Zhou et al.'s 54 percent agreement on invented questions, and Kim et al.'s 60 percent agreement when both models err are all errors that repeats of one model cannot expose. Six developers cannot remove a bias they all share either, but the cross-member agreement figure (F9) can at least show it, and a single model at k = 3 cannot. Chen et al. 2024 add that repeats sharpen the confident-wrong answer on hard queries; every scenario here is a hard query.
3. The pilot numbers say members matter at least as much as repeats: between-member variance 1.3 to 1.5 times the repeat variance for p and t, 0.8 to 1.0 times for the rest, and that was with three models of one developer, which is the case where Kim et al. predict the between-member spread to be smallest.
4. The ensemble is what the literature validated for this task class. The result that an LLM panel matches a human crowd on probabilistic forecasts (Schoenegger et al. 2024) was obtained with a twelve-model, six-country crowd; the single-model result on the same platform (Schoenegger and Park 2023) was a Brier score of 0.20 against the crowd's 0.07. Verga et al. 2024 got better human agreement from three cheap models of three families than from GPT-4, at a seventh of the cost, and less self-preference.
5. Cost does not decide it. The whole recommended run is USD 56 central; a single Opus 5.5 at the same call count is USD 240. The ensemble is the cheaper design and the one whose disagreement is observable.

What the counter-argument does earn: the members should all be competent, the pool should stay equal-weight rather than trust any member more (docs/DESIGN.md section 6 retired member weighting), and the extended report should show per-member central estimates so a reader can see whether any one member dominates the pooled median. If F9 shows one member far from the others on many scenarios, that is a finding about the member, to report, not a reason to drop it after the fact. If the smoke test shows a member's validity rate well below the others, swap it for the next alternate before the run, not after.
