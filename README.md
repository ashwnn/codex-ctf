# codex-ctf

A Codex CLI setup for authorized attack/defense CTF work. It starts an agent team, gives each specialist a clear job, and keeps traffic evidence, findings, patches and captured flags in a private workspace.

**Codex is the harness.** It runs the agent loop, tools, sessions and native subagents. This repository supplies configuration, prompts, skills and small local utilities. It does not run a separate orchestrator or model router. All configured model requests use OpenRouter's Responses API.

## Quick start

Requirements: Codex CLI 0.159.2+ and Bash 3.2+. Python 3.9+ is used for local evidence tools and tests. Docker and TShark are optional.

```bash
git clone https://github.com/ashwnn/codex-ctf.git
cd codex-ctf
export OPENROUTER_API_KEY="..."
./codex-ctf
```

The launcher creates `workspaces/default/`, installs an isolated Codex configuration in `.runtime/codex/`, and opens the native Codex terminal UI. Your regular `~/.codex` setup is left alone. You can also put the key in `.runtime/secrets/openrouter.key` with `0600` permissions. Do not commit keys, challenge data or flags.

For a named service:

```bash
bin/ctf-codex init my-service
# Add deployed source to workspaces/my-service/source/ and captures to evidence/raw/.
# Fill in service.toml and team.toml from the actual event documentation.
bin/ctf-codex team --workspace workspaces/my-service
```

The default model is `stealth/space-bunny-alpha`. It was a time-limited free preview when last checked on October 1, 2026, with a listed October 5 expiry. Run `bin/ctf-codex models` to check availability and key budget. There is no automatic fallback; choose another OpenRouter model or profile explicitly if needed.

## How the harness works

![Codex CTF agent and harness architecture](docs/architecture.svg)

1. **Launcher:** `bin/ctf-codex` installs the repository's config, custom agents, prompts and skills under an isolated `CODEX_HOME`, chooses a profile and starts Codex. Shell and Python do not choose agent actions.
2. **Codex:** The native agent loop sends model requests through the selected OpenRouter provider, invokes local tools, and keeps the session. The `team` profile enables native subagents; other profiles run a single agent.
3. **Coordinator:** A team launch starts five children: flagkeeper, traffic, Docker logs, code review and PoC development. The coordinator assigns work, records agent IDs, relays urgent updates and keeps one code/deployment writer per service.
4. **Shared workspace:** Workers read service context, source and bounded evidence. They link results with a finding ID and write handoffs to `coordination/` and `findings/`. Raw captures and real flags stay in ignored local paths.
5. **Flagkeeper:** Producers pass inbox file paths and counts. A private SQLite ledger deduplicates flags and tracks published expiry. Submission requires a separate, explicit user signal and a configured event API.

`/prompts:brrr` inside the TUI requests an offense-focused surge. It can expand toward 20 children when there are distinct tasks, while keeping flagkeeper and checker uptime covered. `bin/ctf-codex brrr --workspace workspaces/my-service` starts a separate surge session. It does not invent targets or submit held flags.

## What is included

| Part | Purpose |
| --- | --- |
| `config/codex/` and `config/agents/` | OpenRouter provider, task profiles and native specialist roles |
| `prompts/` and `skills/` | Team, audit, traffic, patch and surge workflows; 15 task skills selected by Codex or invoked with `$ad-ctf-*` |
| `templates/` | Service context, team settings and workspace instructions |
| `scripts/pcap-index.py` | Bounded PCAP metadata extraction with frame and stream provenance; no packet bodies |
| `scripts/flag-ledger.py` | Private flag deduplication, expiry planning and receipt tracking |
| `scripts/submit-http.py` | Optional transport adapter after matching the published API and testing locally |
| `bin/ctf-codex` | Setup, launch, model checks, diagnostics and smoke test |

The skills cover inventory, service and code audit, traffic and Docker logs, reproduction, binary and crypto analysis, PoC development, defense, team coordination and flagkeeping. Use `/skills` in Codex to browse them. Use `/prompts:team`, `/prompts:audit`, `/prompts:traffic`, `/prompts:patch` or `/prompts:brrr` for the installed prompts.

## Common commands

```bash
bin/ctf-codex doctor                       # Validate profiles and installed assets; no inference
bin/ctf-codex models                       # Check the selected OpenRouter model
bin/ctf-codex audit --workspace workspaces/my-service
bin/ctf-codex traffic --workspace workspaces/my-service
bin/ctf-codex patch --workspace workspaces/my-service 'Fix finding my-service-001.'
bin/ctf-codex smoke                        # Live model and tool-loop check; may use credits
python3 -m unittest discover -s tests -v
```

The `team` profile uses low reasoning effort by default. `audit` and `patch` use high effort. `cheap` and `traffic` use low effort. `deepseek-cheap` and `deepseek-audit` explicitly select DeepSeek V4.1 Flash through OpenRouter. Set a different profile with `--profile` or a model with `--model VENDOR/MODEL`.

Command tools run in Codex's workspace-write sandbox with network off by default. This limits tool execution, not what is sent to the selected model provider: model-visible snippets and tool output go to OpenRouter. Review and redact evidence before giving it to Codex. The local workspace is Git-ignored, but it is not an OS security boundary. An interactive session may still ask for native sandbox escalation.

For design details and operational assumptions, see [design decisions](docs/design.md), the [A/D operating map](docs/ad-playbook.md) and the [verification record](docs/verification.md). Actual service targets and event API details must come from the event, not these templates.
