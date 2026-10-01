# codex-ctf

An A/D CTF workspace powered by the **native Codex CLI harness**. Codex handles
reasoning, tool calls, edits, follow-up turns, compaction, sessions and skill
selection. TOML config, AGENTS.md, custom agents and skills define the workflow.
Shell/Python handle setup, launch, diagnostics and local evidence/flag transport;
they do not implement an agent loop or decide delegation.

All configured inference goes directly to OpenRouter's Responses endpoint.
Default: **`stealth/space-bunny-alpha`**, low reasoning effort. Audit and patch
profiles use high effort. There is no automatic model or provider fallback.
The user requested A/D-only operation without phase/model-eligibility gates.

## Start

```bash
cd ~/Repositories/codex-ctf
./codex-ctf
```

That opens the native Codex terminal UI with the isolated OpenRouter config and
asks the primary agent to start five native specialists: flagkeeper, traffic,
Docker logs, code review and PoC development. It prepares a private workspace
at `workspaces/default/`. Their native IDs and assignments go in
`coordination/roster.md`; workers communicate through shared role inbox files
and durable handoffs. The primary relays urgent messages using native tools.
Direct sibling messaging was unavailable in a synthetic CLI test.
The primary scales as the service backlog warrants, up to twenty children.

For an explicit point-focused surge inside that session, type
`/prompts:brrr` (or ask for `$ad-ctf-brrr`). Codex custom prompts are documented
under `/prompts:<name>`, so bare `/brrr` is not a registered native CLI command.
`bin/ctf-codex brrr --workspace workspaces/default` starts a new surge session.
The surge reuses workers where possible and aims for twenty useful roles;
it does not create fake targets or submit held flags.

## Optional tooling

Requires Codex CLI **0.159.2+** and Bash 3.2+. Python 3.9+ is needed only for
metadata/evidence tooling and tests. Wireshark/tshark and Docker are optional.

```bash
bin/ctf-codex setup
bin/ctf-codex doctor
bin/ctf-codex models
bin/ctf-codex smoke
bin/ctf-codex init my-service
bin/ctf-codex team --workspace workspaces/my-service
bin/ctf-codex brrr --workspace workspaces/my-service
```

Put deployed service source in `workspaces/my-service/source/` and original
captures/logs in `evidence/raw/`. Fill `service.toml` and `team.toml` from the
actual service description, runtime and published API. Workspaces created by
`init` and all runtime state are Git-ignored. When using an external directory
with `--workspace`, keep it private and ensure its own repository ignores
challenge evidence and findings.

The supplied temporary key is stored locally at
`.runtime/secrets/openrouter.key` with permissions `0600`; it is never written
to tracked config. On another machine, set `OPENROUTER_API_KEY` in the launching
shell or create that private local file. Do not commit it or paste it into prompts.
The auth helper checks the environment first, then the local file.

## Use native Codex directly

Setup writes a dedicated **user-level** config under `.runtime/codex/`.
Your regular `~/.codex` config, login and sessions are untouched. `CODEX_HOME`
points Codex at this dedicated installation; provider keys do not belong in
project `.codex/config.toml` files.

```bash
CTF_HOME="$PWD/.runtime/codex"
env CODEX_HOME="$CTF_HOME" codex --no-daemon --strict-config \
  --profile audit --cd workspaces/my-service \
  'Use $ad-ctf-service-audit to audit the deployed source and save findings.'
```

Use `/skills`, `/agent`, `/status`, `/model` and `/compact` inside Codex. Ask it to save a
finding handoff before compaction or changing models. The current default model
catalog controls available efforts and tools. The full native CLI remains
available; this repository does not implement an alternative agent loop.

## Convenience launchers

```bash
bin/ctf-codex audit --workspace workspaces/my-service
bin/ctf-codex traffic --workspace workspaces/my-service
bin/ctf-codex patch --workspace workspaces/my-service 'Fix finding my-service-001 locally.'

# Headless native Codex run; findings are saved by the skill in the workspace.
bin/ctf-codex audit --workspace workspaces/my-service --exec --json \
  'Focus on object ownership around flag retrieval.'

# Explicit alternative through the same OpenRouter provider.
bin/ctf-codex audit --workspace workspaces/my-service --profile deepseek-audit
```

| Profile | Model | Effort | Purpose |
| --- | --- | --- | --- |
| team | Space Bunny Alpha | low | Native five-worker team, expandable to twenty |
| cheap | Space Bunny Alpha | low | Inventory and focused edits |
| traffic | Space Bunny Alpha | low | Evidence triage and timeline |
| audit | Space Bunny Alpha | high | Root cause and flag paths |
| patch | Space Bunny Alpha | high | Narrow fixes and regressions |
| deepseek-cheap | DeepSeek V4.1 Flash | low | Explicit inexpensive alternative |
| deepseek-audit | DeepSeek V4.1 Flash | high | Explicit deeper alternative |

Change defaults in `config/codex/*.toml`; setup refreshes generated copies on
every launch. Current Codex uses separate `<name>.config.toml` profile files.
Model catalog discovery uses command-based auth. No key, reasoning metadata or
context-window estimate is hard-coded into a custom model catalog.

As verified September 30, 2026, OpenRouter lists Space Bunny Alpha as free with
a 1M context window and an **October 5, 2026 expiration date**. Check `models`
before use. DeepSeek supports low/high/max; medium is not advertised. These
profiles stay on the exact selected slug and fail if it becomes unavailable.
[Space Bunny Alpha](https://openrouter.ai/stealth/space-bunny-alpha),
[DeepSeek V4.1 Flash](https://openrouter.ai/deepseek/deepseek-v4.1-flash).

## Evidence and handoffs

`service.toml` holds deployment, ingress, checker, tick, flag-lifetime and writer
details. Specialists use a shared `findings/<service>-NNN.md` record with precise
evidence, confidence, reproduction, patch status, verification and rollback.

The dedicated flagkeeper keeps captured flags in an ignored private SQLite
ledger. Producers write JSONL files to `flags/inbox/`; agent messages contain
only paths and counts. The ledger deduplicates, tracks published expiration and
reports how many flags would be lost by a planned submission time. Submission
requires a separate explicit user signal and the actual documented event API.
`scripts/submit-http.py` is an opt-in transport adapter only when the published
API matches its JSON contract; it is tested against a local mock, not the event.
The event's five-tick lifetime means an end-of-event flush cannot score older
expired flags even though sandbagging itself is permitted.

```bash
python3 scripts/pcap-index.py workspaces/my-service/evidence/raw/service.pcap \
  --port 8080 --max-packets 20000 \
  --output workspaces/my-service/evidence/derived/index-001
```

The tool extracts local metadata, not bodies or attack payloads. Codex then
interprets reviewed, redacted derived evidence. Capture hashes and frame/stream
numbers retain provenance. TLS, packet gaps, proxy/NAT and scan truncation remain
explicit limitations. Raw evidence stays unchanged.

OpenRouter receives model inputs and tool outputs; the stealth provider may
retain prompts/completions. Instructions to redact secrets are a workflow
contract, not automatic DLP. Review selected snippets locally before exposing
them to Codex. Workspaces are private by Git convention, not OS isolation.

Command tools use workspace-write, network off, filtered environment and no
login shells. Apps, plugins, hooks, memories and auto reviewers are disabled.
Only the explicit `team` profile enables native subagents; standalone
audit/traffic/patch profiles remain single-agent. The launcher uses
`--no-daemon` to avoid inheriting a personal daemon.
No phase gate is implemented. Sandbox escalation still follows native Codex
behavior; headless `exec` cannot ask for escalation, so run local tests that fit
the sandbox or use the interactive CLI when needed.

## Verify and extend

```bash
python3 -m unittest discover -s tests -v
bin/ctf-codex doctor
bin/ctf-codex smoke
```

`doctor` uses native prompt construction to validate all seven profiles and skill
discovery, without model inference (it may fetch catalog metadata). The installed
CLI does not support `--strict-config` on diagnostic subcommands; runtime launches
use it. `smoke` tests real inference, shell, apply_patch and tool-result replay
inside an ignored synthetic workspace. It invokes the selected model and may
consume credits for a nonfree default.

See [design and reference decisions](docs/design.md) and the canonical
[configuration](config/codex/config.toml). No challenge service or PCAP was included
in the supplied archives; those archives contained the two skill definitions.
The [verification record](docs/verification.md) covers the completed native
tool-loop and cross-skill synthetic tests.
The [A/D operating map](docs/ad-playbook.md) explains the agent handoffs,
scaling, Docker/traffic workflow and sandbagging tradeoff.
