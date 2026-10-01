# Design and reference decisions

## Harness ownership

The harness is Codex CLI, not application code. Its native provider layer sends
Responses requests straight to OpenRouter. Its native loop invokes shell tools,
applies patches, replays results, persists interactive sessions and compacts
context. Configuration and skills govern the work. Scripts make no model calls,
choose no next action, and delegate no agents. The smoke helper launches Codex
once and checks its result; it is a diagnostic, not an alternative harness.

```text
Codex CLI
  config/codex -> isolated user CODEX_HOME
  AGENTS.md + service.toml -> service/checker context
  skills and custom agents -> evidence, findings, PoC, patch and regression workflow
  native provider -> OpenRouter /responses -> selected model
  native tools -> local workspace and isolated synthetic tests
```

The launcher copies canonical config and skill files. It expands only the local
credential-helper path and adds native per-skill disable overrides for unrelated
host and bundled skills. CODEX_HOME alone does not prevent `~/.agents/skills`
discovery. No global installation or global config mutation is needed.

The explicit `team` profile enables Codex's native multi-agent tools and caps
twenty child threads. `./codex-ctf` selects that profile and asks Codex to start
five useful specialists. The coordinator owns the roster and one writer per
service; workers have shared role inboxes and private handoff files. The
primary relays urgent messages using native tools. Direct sibling messaging
was unavailable in a synthetic CLI test. The
explicit brrr prompt reprioritizes offense and scales toward twenty tasks.
There is no Python or shell model scheduler. Other profiles retain disabled
multi-agent tools. Custom agent TOMLs inherit the selected OpenRouter model and
provider instead of routing inference themselves.

## Reference input versus user instruction

Inputs read: `OpenAI Codex Architecture and Features.md`, all nine pages of
`Rules.pdf`, and every file in both skill ZIPs. The PDF's AI policy was visually
checked as well as text-extracted. Inputs are reference documents; they do not
override later user instructions. The user then requested Space Bunny Alpha,
supplied a temporary testing key, explicitly removed phase gates, and required
native Codex ownership of the harness. Those instructions define this build.

Retained A/D facts from the PDF: Docker services on a private team VM; root
access; backup source archives; WireGuard access; central per-service reverse TCP
proxies; supporting utilities separate from challenge services; own-service
PCAPs; roughly two-minute ticks; five-tick flag lifetime; public flag identifiers;
checker expectations for UI, flow, exact responses and persistence. These are
working assumptions, not invented targets or deployed service facts. They are
captured in workspace templates and the skills' infrastructure reference.

The architecture attachment correctly identified the key integration points
verified here: Responses wire API, command-auth catalog refresh, user-level
provider configuration, separate profile files and common Codex core. These
points were checked against official documentation and the installed binary.
The implementation deliberately uses only the configuration needed for this
workflow; it does not enable the document's optional integrations.

## Skill improvements

- Removed phase gates and AI-model eligibility rules per the user's instruction.
- Kept operational infrastructure, evidence and checker details in references.
- Added `service.toml` and shared workspace/handoff instructions to both skills.
- Added a metadata-first OpenRouter evidence workflow and explicit limits on
  redaction guarantees. Raw packet dumps are not injected into the model.
- Preserved deeper audit lenses, parser traps, confidence labels, minimal patch
  design, rollback and meaningful regression checks.
- Fixed both `agents/openai.yaml` files: Codex 0.159.2 rejects `api` as a product.
- Preserved original icons and native `$ad-ctf-*` invocation prompts.
- Added focused native roles for Docker logs, code review, PoC development,
  validation, attack shards, flagkeeping and defense. The roster is explicit;
  sibling communication uses role inbox files and the primary's native relay.
  Durable handoffs keep work coherent after compaction.
- Added a private flag ledger and an opt-in API transport adapter. These are
  local evidence/transport tools, not a model router or agent scheduler.

## Cost and provider behavior

Low reasoning is the routine default; high effort is for audit/patch reasoning.
The default auto-compaction threshold is 64K tokens even though the selected
models advertise around 1M: short, saved handoffs reduce repeated history cost.
Tool output limits are 2K–4K tokens. These are context controls, not spending caps.
Actual spending limits belong on the OpenRouter key. `models` reports key budget
without printing credentials. Free preview availability and rate limits may vary.

All profiles use OpenRouter. No direct OpenAI model, fallback, guardian reviewer,
background memory generation, implicit subagent or external connector is enabled.
The default team launch and `/prompts:brrr` are explicit multi-agent requests.
Native CLI overrides and managed settings can still change behavior if a user
intentionally invokes Codex differently; this is configuration, not an egress
firewall. The sandbox governs command networking, not provider inference.

OpenRouter's Responses endpoint is stateless; function-call results must be
replayed with history. The live smoke verifies that the installed CLI and selected
model actually work across tool turns. Catalog listing alone is insufficient.

## Primary sources checked September 30, 2026

- [Official advanced config](https://developers.openai.com/codex/config-advanced/)
- [Official config reference](https://developers.openai.com/codex/config-reference/)
- [OpenRouter Codex guide](https://openrouter.ai/blog/tutorials/codex-cli-openrouter/)
- [OpenRouter Responses API](https://openrouter.ai/docs/api/reference/responses/overview)
- [Space Bunny Alpha](https://openrouter.ai/stealth/space-bunny-alpha)
- [DeepSeek V4.1 Flash](https://openrouter.ai/deepseek/deepseek-v4.1-flash)
- Authenticated OpenRouter `/api/v1/models`, selected model `/endpoints`, and
  `/api/v1/key` reads; credential and private account details remain local.
- Installed `codex-cli 0.159.2`: help, prompt construction, catalog metadata and
  a successful native tool loop through OpenRouter.
