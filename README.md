# codex-ctf

Codex CLI configuration for an authorized attack/defense CTF. Codex runs the
agent loop and tools; this repository supplies the OpenRouter configuration,
specialist agents, skills and local evidence utilities.

## Start

Requires Codex CLI 0.159.2+ and Bash 3.2+. Python 3.9+ is needed only for the
optional evidence and deployment utilities.

On this Windows host, run the commands in Ubuntu/WSL. The installed Windows
Codex CLI rejects shell tools; the Ubuntu CLI completed the live tool loop.

```bash
git clone https://github.com/ashwnn/codex-ctf.git
cd codex-ctf
export OPENROUTER_API_KEY="..."
./codex-ctf
```

The terminal UI opens without sending a prompt. Tell Codex what you know about
your assigned VulnBox, connection, event rules and services in your first
message. Give partial information if that is all you have. Codex derives the
rest from available organizer material and the machine, starts its specialist
team, and asks only when a required fact cannot be found. No `init` command,
service manifest or named workspace is required.

The launcher works from the repository root. It installs an isolated Codex
configuration in ignored `.runtime/codex/` and stores private event artifacts
under `.runtime/`, including session logs for per-agent token accounting. Your
normal Codex configuration is unchanged. The default
model is `stealth/space-bunny-alpha`; all default agents inherit it. Select a
different OpenRouter model explicitly if that preview is unavailable. No
provider fallback occurs.

Free OpenRouter models have daily request limits. A long `/prompts:brrrr` run
can exhaust them; the provider's 429 response includes the reset time. The
harness stops at that limit and retains its session logs for continuation.

Within the TUI, `/prompts:brrrr` switches to a points-first surge with more
agents for distinct useful work. `/prompts:chillax` switches to a low-token
workflow with the primary agent and at most one useful worker. Codex CLI names
custom prompt commands `/prompts:name`; bare `/brrrr` and `/chillax` are not
native slash commands.

## Scope and flag handling

The assigned VulnBox and its documented service interfaces are the default live
scope. Codex verifies the exact address and ports before requests, and does not
enumerate ports or contact other teams or event infrastructure. Command network
access is enabled for the three-step workflow. These instructions do not enforce
an outbound firewall; use an external allowlist when hard network containment is
required. Captured flags stay private. Submission requires a separate, current
instruction from you.

## Optional commands

```bash
./codex-ctf doctor                 # Validate local configuration without inference
./codex-ctf models                 # Check the configured model and account metadata
./codex-ctf smoke                  # Live model and local tool check
./codex-ctf resume --last          # Resume the last session interactively
./codex-ctf resume --exec --json SESSION_ID -- "Continue the saved task"
```

`bin/ctf-codex` also exposes audit, traffic, patch, model selection and local
deployment utilities. They use the same repository root and isolated Codex
configuration. The checked-in `templates/` files are optional examples for
checker and patch records; the user does not fill them before starting.
