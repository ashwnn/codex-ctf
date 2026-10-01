# Model selection and personal budget

**Decision, 2026-10-01:** use DeepSeek V4.1 Flash as the low-cost root and
high-volume-worker baseline. Use MiMo V2.6 Flash for PoC construction and MiMo
V2.6 Pro for audit, code review and defense. These are provisional role
hypotheses based on current ZDR-route cost and throughput data, not A/B winners.
The paid comparison is blocked until this OpenRouter account has purchased
credits. The user’s total personal competition budget is approximately **$60**.

## Why this starting mix

OpenRouter’s ZDR endpoint catalog was queried on October 1, 2026. Prices and
provider performance vary by route; the entries below are observed endpoints,
not guaranteed selections. P50 latency and generation throughput are
short-window catalog telemetry. Model pages also list tool calling for these
families. Recheck with `bin/ctf-codex models --zdr MODEL...` before the event.

| Candidate and proposed role | Example ZDR route | Input / output per 1M tokens | P50 latency / throughput | Initial judgment |
| --- | --- | ---: | ---: | --- |
| DeepSeek V4.1 Flash — coordinator and high-volume workers | Morph | $0.053 / $0.432 | 0.97 s / 84 tok/s | 27 eligible routes; another route reached 225 tok/s at $0.30 / $1.20 |
| MiMo V2.6 Flash — PoC development | Novita | $0.14 / $0.28 | 3.43 s / 37 tok/s | Three eligible routes; current uptime/latency data merits a live comparison |
| MiMo V2.6 Pro — audit, code review and defense | DeepInfra | $0.43 / $0.87 | 2.65 s / 21 tok/s | One eligible route; keep it for bounded reviews, not coordination |
| GLM 5.3 Flash — high-volume challenger | OpenInference | $0.02 / $0.30 | 3.04 s / 10 tok/s | 28 eligible routes; BaseTen reached 147 tok/s at $0.15 / $0.50 |
| GPT-6 Luna — alternative for high-volume work | Azure | $0.10 / $0.50 | 3.25 s / 62 tok/s | ZDR route exists; compare only if OpenAI-group ZDR is active |
| GPT-6.1 Sol — occasional difficult review | Azure | $2.00 / $10.00 | 5.64 s / 42 tok/s | High cost and no throughput advantage; not the routine default |

These snapshots do not predict CTF performance. The fastest and lowest-cost
endpoint are not always the same route; the GLM and DeepSeek rows show a large
spread. OpenRouter routes among eligible endpoints, so capture actual billed
cost and selected provider for each trial. This makes GLM 5.3 Flash the most
useful additional high-volume challenger to test, not an automatic replacement
for DeepSeek. DeepSeek’s own catalog lists V4.1 Flash at $0.0264/$0.60 per
million, while ZDR endpoints can have different provider pricing. The current
`config/agents/*.toml` choices use native Codex model settings;
the remaining specialists inherit the selected root model. No custom router is
present. [Codex custom-agent files support per-role `model` and
`model_reasoning_effort`](https://developers.openai.com/codex/multi-agent).

### Per-role starting assignments

| Role | Model | Effort | Why |
| --- | --- | --- | --- |
| Root coordinator | DeepSeek V4.1 Flash | low | Fast handoffs and context synthesis across workers |
| Flagkeeper, traffic, Docker logs, inventory, reproduction, attack and PoC test | DeepSeek V4.1 Flash | low | Bounded extraction, state checks and high task volume |
| PoC developer | MiMo V2.6 Flash | low | Code-producing work with a lower output-token rate than Pro |
| Audit, code review, defense | MiMo V2.6 Pro | medium | Complex trust-boundary reasoning and checker-preserving edits justify testing a stronger tier |
| Verifier | DeepSeek V4.1 Flash | low | The tests and checker evidence should decide results; use a low-cost independent verification pass |

The five explicit child overrides are hypotheses, not eligibility rules. They
remain manually editable. A `--model` launch override controls the root and
agents that inherit its model; an explicit custom-agent model takes precedence.
If trial evidence does not support the Pro/Flash split, remove or change those
few TOML overrides. Reasoning effort is held low/medium to start; increase it
only where a same-model comparison shows a meaningful correctness gain.

## A/B method and current result

The synthetic fixtures in `benchmarks/model-selection/` exercise three roles:
source audit, evidence-bounded traffic triage, and a checker-contract-preserving
authorization patch. Run every candidate in a clean copy with the same Codex
CLI, effort, prompt, fixture and offline tool settings. Alternate run order;
repeat close results. Score deterministic tests and response contract checks,
then record wall-clock completion time, tool calls, retries, corrections, actual
billed cost and unsupported claims. Select by **correct tasks per minute**, with
**cost per successful task** as the budget constraint. Raw tok/s and generic
leaderboards are secondary.

On October 1, I attempted the patch task through the native Codex/OpenRouter
Responses loop with DeepSeek V4.1 Flash. OpenRouter returned HTTP 402 before
inference: the account has never purchased credits. A zero-priced Qwen 3.8 27B
Free attempt returned HTTP 429 before inference. Neither run was charged, and
neither produced a model result. The exact status and $0 cost are recorded in
`benchmarks/model-selection/README.md`. This means the role mix above is a
cost/latency-led starting policy, **not a completed A/B conclusion**.

## ZDR and route checks

The account must enforce ZDR for every model group used. In particular, the
OpenAI-family alternatives require the OpenAI ZDR group, while the open-weight
candidates require the non-frontier group. OpenRouter’s `/endpoints/zdr` API
shows which provider endpoints qualify but does not report whether account/key
enforcement is active. The `models --zdr` command makes this endpoint check easy;
the account control or assigned guardrail remains the enforcement boundary.
Avoid the temporary `stealth/space-bunny-alpha` preview for competition inputs:
its provider is not a suitable ZDR endpoint, it expires October 5, and its
free-preview status does not establish a safe event route.

ZDR applies to inference-provider retention. Prompts are still processed by the
provider; local tools and output files need their own controls. Keep A/B content
synthetic and retain test logs under ignored `.runtime/`. The OpenRouter account
and key ZDR controls are not visible in the key metadata available to this
harness, so this record does not certify their current state.

## $60 allocation

| Use | Cap |
| --- | ---: |
| Pre-event A/B and regression trials (hard cap) | $5 |
| Routine competition work | $40 |
| Deliberate difficult-task escalation | $10 |
| Unallocated reserve | $5 |
| **Total** | **$60** |

The full harness and competition share this $60 cap. Set the OpenRouter key
limit to the remaining personal budget and watch actual usage before and during
the event. Treat $5 as evaluation’s hard ceiling; keep the reserve unspent
unless needed. Reasoning counts as output usage, and repeated tool turns resend
conversation history. Large teams can multiply those requests, so use the
configured five workers first and scale only when there are distinct unowned
tasks. Twenty is a concurrency ceiling, not a target.

## Why CyberGym is context, not the selector

CyberGym covers 1,507 real-world vulnerabilities across 188 projects and
measures whether an agent can reproduce real vulnerabilities. Its original
evaluation found that even its best tested combination (OpenHands with Claude
3.7 Sonnet) reproduced 11.9% of cases. CyberGym-E2E expands toward end-to-end
discovery, PoC creation and patch generation. These are valuable signals that
security work is difficult, but the reported models and harnesses do not include
the OpenRouter endpoints and Codex team used here. Do not transfer its score to
these candidates. Validate locally against published, permitted benchmark tasks
and then against the competition’s own checker, flag lifecycle and uptime.

Sources: [CyberGym paper](https://arxiv.org/abs/2506.02548),
[CyberGym-E2E paper](https://arxiv.org/abs/2606.04460),
[OpenRouter ZDR endpoint API](https://openrouter.ai/docs/api/api-reference/endpoints/list-endpoints-zdr),
[OpenRouter guardrails](https://openrouter.ai/docs/guides/features/guardrails/overview),
[DeepSeek V4.1 Flash](https://openrouter.ai/deepseek/deepseek-v4.1-flash),
[MiMo V2.6 Flash](https://openrouter.ai/xiaomi/mimo-v2.6-flash),
[MiMo V2.6 Pro](https://openrouter.ai/xiaomi/mimo-v2.6-pro),
[GLM 5.3 Flash](https://openrouter.ai/z-ai/glm-5.3-flash).
