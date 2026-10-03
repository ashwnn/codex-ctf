# codex-ctf

Codex CLI configuration for an authorized attack/defense CTF. The intended flow
is simple: enter this repository, run Codex, then send what you know about your
assigned VulnBox and event. Codex coordinates the investigation from there.
This repository supplies the OpenRouter configuration, specialist agents, skills
and private evidence utilities; Codex owns inference and tool use.

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

The launcher opens the Codex terminal UI without sending a prompt. In your first
message, provide the assigned VulnBox address, connection details, event rules
and known services. Partial information is fine. Codex derives what it can from
organizer material and the assigned machine, then asks for any fact required to
continue. There is no `init` step, required service manifest or named workspace.

## How it works

![Codex CTF architecture: launcher, native agents, target, private artifacts and flag handling](docs/architecture.svg)

`./codex-ctf` starts the native Codex CLI at the repository root. The launcher
installs the repository's profiles, 12 agents, 16 skills and prompts in an
isolated `.runtime/codex/` home. It leaves your normal Codex configuration
alone. It does not implement a separate agent loop.

After your first message, the primary agent establishes the exact authorized
target and documented service interfaces. It starts bounded inventory, traffic,
Docker log, code review and flagkeeper roles. They share short handoffs under
ignored `.runtime/`; useful PoC, patch and verification work follows concrete
findings. The team uses synthetic records to reproduce issues, checks normal
flows and rollback after a patch, and records what was actually observed.

Captured flags stay under `.runtime/flags/`. When
`.runtime/flags/submission.json` exists with the organizer-published API
contract, the launcher starts a private worker that polls the inbox every
second and submits pending flags. The worker stops with Codex and logs
counts only to `.runtime/flags/auto-submit.log`. Without that configuration,
flags remain held. Use `CTF_SUBMISSION_ADAPTER` when the official API does not
match the generic HTTP adapter. Never guess the endpoint or status mapping.
Sessions and event evidence remain under `.runtime/` and out of Git.

## Scope and modes

The assigned VulnBox and its documented service interfaces are the default live
scope. Codex verifies the exact address and ports before requests, and does not
enumerate ports or contact other teams or event infrastructure. Command network
access is enabled for this workflow. Prompt instructions are not an outbound
firewall; use an external allowlist if hard network containment is required.

The default OpenRouter model is `deepseek/deepseek-v4.1-flash`; default agents
inherit it. Use `--profile mimo` to select `xiaomi/mimo-v2.6-flash` explicitly.
There is no automatic model fallback. Provider errors stop the run and retain
sessions for continuation.

Within the TUI, `/prompts:brrrr` expands distinct useful work, up to twenty
agents. `/prompts:chillax` uses the primary agent and at most one worker.
Codex CLI names custom prompt commands `/prompts:name`; bare `/brrrr` and
`/chillax` are not native slash commands.

## Optional commands

```bash
./codex-ctf doctor                 # Validate local configuration without inference
./codex-ctf models                 # Check configured model and account metadata
./codex-ctf smoke                  # Live model and local tool check
./codex-ctf resume --last          # Resume the last session interactively
./codex-ctf resume --exec --json SESSION_ID -- "Continue the saved task"
```

`bin/ctf-codex` also exposes audit, traffic, patch, model selection and local
deployment utilities. The checked-in `templates/` files are optional examples
for checker and patch records.

## Verification

On 2026-10-02, the Python suite ran 71 tests with one optional `tshark` skip.
It covered launcher dispatch and resume, provider isolation, evidence and flag
tools, and deployment recovery with temporary repositories and dummy adapters.
The previous checks covered shell syntax, seven then-existing strict Codex
profiles, native prompt construction and diff whitespace. In Ubuntu/WSL, a live smoke completed model
inference, shell read, file write and replay using the former free preview. The
current model configuration has not been live-smoke-tested.

The full and `brrrr` loops were exercised on an authorized offline FAUST clone
through four documented service interfaces. Synthetic IMC and LAMP attacks were
reproduced, patched, rolled back and replayed with normal-flow checks. An ALF
parser crash was confirmed, but flag access and RCE were not. A provider 429
interrupted the ALF and Rufflecopter closeout, and `chillax` was not exercised
live. No official checker, competition network, live flag submission or score
was available, so these checks do not establish that every feature works in a
competition. See [verification details](docs/verification.md).
