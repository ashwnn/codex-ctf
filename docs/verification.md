# Verification — October 1, 2026

Validated locally with `codex-cli 0.159.2`, using the supplied temporary key.
All model runs used `stealth/space-bunny-alpha` through OpenRouter.

| Check | Result |
| --- | --- |
| Native config/prompt construction | All seven profiles load without warnings |
| Native catalog discovery | Exact stealth and DeepSeek slugs, context and supported efforts present |
| Skill discovery | Both CTF skills present; unrelated host/bundled skills absent |
| Runtime strict config | Successful native exec runs with `--strict-config` |
| Live tool-loop smoke | Shell read, apply_patch, shell re-read and exact final response passed |
| Traffic skill integration | Saved finding from synthetic derived traffic and source evidence |
| Audit/patch skill handoff | Continued same finding ID, confirmed synthetic root cause and applied local fix |
| Patch regressions | Normal response shapes preserved, cross-owner reads denied, missing IDs unchanged |
| Rollback | Original saved, restored/reproduced, patch re-applied and reverified by Codex |
| Independent patch check | Authorized read succeeds; cross-owner read raises KeyError |
| Tooling tests | 25 passed, including setup refresh, version rejection, private PCAP modes, and actual tshark extraction |
| One-command terminal UI | `./codex-ctf` opens native Codex; `/status` shows Space Bunny Alpha, OpenRouter and local workspace |
| Credential handling | Private key mode 0600; no key in tracked/nonignored files |
| Budget read after tests | OpenRouter reported usage $0; $1 temporary-key limit remaining |

The local synthetic fixture and logs live only in ignored `workspaces/harness-smoke`
and `.runtime/`. They are not competition artifacts. No live challenge service,
peer, scoring system, checker tick or remote deployment was tested. The real
checker contract still has to be supplied per service.

Space Bunny Alpha's catalog advertises expiration on October 5, 2026. Availability,
limits and prices should be rechecked with `bin/ctf-codex models`. No automatic
fallback is configured.
# Native A/D team extension - October 1, 2026

- `python3 -m unittest discover -s tests -v`: 23 tests passed. This includes
  private flag-ledger lifecycle, expiry, duplicate handling, partial/ambiguous
  receipts, timeout behavior, the mock submission adapter and native launcher
  argument contracts. No live flags or event endpoint were used.
- `bash -n bin/ctf-codex codex-ctf`, Python compilation and TOML parsing passed.
- `bin/ctf-codex setup` installed 12 custom agent roles and 13 A/D skills in
  the isolated user-level `CODEX_HOME`. Native `debug prompt-input` discovered
  the team, surge and universal skills; `prompts/brrr.md` was installed.
- The installed Codex 0.159.2 loaded the generated `team` profile with
  `--strict-config` and reported the selected OpenRouter model/provider,
  workspace sandbox and low reasoning effort. A deliberately failing auth
  command stopped the run before inference; this checks configuration loading
  but is not a live multi-agent or provider smoke test. The diagnostic
  `debug prompt-input` subcommand itself does not accept `--strict-config`.
- A synthetic OpenRouter run spawned one child, sent a native follow-up and
  waited successfully (`NATIVE_TEAM_OK`). A second run spawned two children
  and attempted direct sibling PING/PONG. Both children reported no native
  `send_input` tool, so direct peer messaging is unavailable in this tested
  CLI/model setup (`PEER_CHAT_UNVERIFIED`). The shared role inbox and primary
  relay protocol is the supported communication path; no daemon was added.
- No live service, published target list, event API contract, checker or PCAP
  has been supplied. PoC efficacy, actual twenty-worker scaling and flag
  submission remain unverified until an authorized event workspace is available.

# Configuration validation and skill expansion — October 1, 2026

Re-verified against the installed `codex-cli 0.159.3` (repository floor 0.159.2);
the previously installed 0.157.1 was below the floor and could not run `setup`.
No OpenRouter key was present in this checkout, so no live inference was run.

| Check | Command | Result |
| --- | --- | --- |
| Unit tests | `python3 -m unittest discover -s tests -v` | 33 tests, 32 passed, 1 skipped (`tshark` absent) |
| Shell syntax | `bash -n bin/ctf-codex codex-ctf bin/openrouter-token` | clean |
| Python syntax | `ast.parse` on all four scripts | clean |
| Strict config | `bin/ctf-codex doctor` | strict-config OK for all 7 profiles, no inference |
| Prompt/skill discovery | `bin/ctf-codex doctor` | all 7 profiles OK; 15 skills and 12 agents discovered |
| Native environment | `codex doctor --summary` | 20 ok, 1 idle, 0 warn, 0 fail |
| Managed assets | `bin/ctf-codex doctor` | installed counts equal source counts |
| New skills | `debug prompt-input` validation JSON | `ad-ctf-binary-exploitation` and `ad-ctf-crypto-analysis` present |
| Custom prompts | files under `.runtime/codex/prompts/` | `team`, `audit`, `traffic`, `patch`, `brrr` installed |

Direct evidence gathered during this pass:

- `codex --strict-config exec` with a deliberately bogus top-level key exits 1
  with `Error loading config.toml: ... unknown configuration field`; native
  `codex --strict-config doctor` only warns. `doctor` therefore uses the exec
  path with the provider auth forced to `/bin/false` so no inference occurs.
- A trusted project's `.codex/config.toml` overrides the base model (observed
  `model: project-injected-model`), and a workspace inherits the root's trust;
  marking the root untrusted suppresses `AGENTS.md`, so the launcher instead
  removes planted project config under the workspaces before each launch.
- `untrusted` trust level does not prompt during non-interactive `exec` but does
  suppress `AGENTS.md`, confirming it is not a usable blanket setting here.

Remaining gaps: no OpenRouter key was available, so `models` and `smoke` (live
inference, shell, apply_patch and tool-result replay) were not re-run in this
pass; the TUI `/prompts:` picker was not exercised interactively. Codex `doctor`
was run on Linux only.

## Workspace readiness records — October 1, 2026

- `python3 -m unittest discover -s tests -v`: 41 tests passed. Coverage includes
  workspace readiness records, native session-resume argument forwarding,
  rejection of resume provider/approval overrides, refusal to delete
  unmanaged/symlinked Codex config, hashed flag review, persisted reconciliation
  evidence, migration of existing ledger DBs, and option-looking resume prompts
  remaining positional data.
- `bash -n bin/ctf-codex codex-ctf` and `git diff --check`: passed.
- `bin/ctf-codex doctor`: all seven profiles passed `--strict-config`, native
  prompt/skill discovery passed, and generated assets matched (12 agents, 15
  skills). Native doctor reported 22 ok, 1 idle, 1 note and 1 warning because
  the check ran non-interactively with `TERM=dumb`; no inference was performed.
- Installed `codex-cli 0.159.3` `resume --help` exposes `--last`, session ID,
  profile, working directory and strict-config options used by the wrapper.
- Ledger CLI tests exercised `review` and `receipts` against a synthetic flag;
  outputs contained its digest and receipt reference but not its value.
- Initialized workspace records are templates only. No event-specific checker
  contract, service address, team identifier, API adapter or rollback command
  has been supplied or validated; populate them from published event material
  and local observation before relying on them.

## Runtime preflight and setup behavior

`bin/ctf-codex doctor` reports and enforces the Python 3.9+ prerequisite;
`models` checks it before invoking the Python catalog client. Launch setup
replaces changed managed files atomically and keeps obsolete generated files in
place so another active Codex process cannot lose an agent or skill it has not
loaded yet. A launch sanitizes only its selected managed workspace's planted
`.codex/config.toml`; `setup` does not walk or alter workspaces. If agent or
skill source files are intentionally removed, remove their obsolete installed
copies from the isolated `.runtime/codex` after stopping active sessions.

## Private ledger backup and restore

The flag ledger uses SQLite WAL mode. Do not copy only `ledger.sqlite3` while
the ledger may be active: committed rows may still be in its `-wal` file. Use
SQLite's online backup API to a private, ignored destination, then validate a
restore from a synthetic database before relying on the procedure:

```bash
python3 - <<'PY'
import sqlite3
from pathlib import Path

source = Path("workspaces/SERVICE/flags/ledger.sqlite3")
backup = Path(".runtime/backups/SERVICE-ledger.sqlite3")
backup.parent.mkdir(parents=True, exist_ok=True)
src = sqlite3.connect(source)
dst = sqlite3.connect(backup)
src.backup(dst)
dst.close()
src.close()
backup.chmod(0o600)
PY
```

Replace `SERVICE` with the managed workspace name. Keep the destination under
`.runtime/`, which is ignored and private. For restore, stop ledger writers,
copy the backup to a new private path, and open it with
`python3 scripts/flag-ledger.py --db PATH status`. Compare the redacted counts
and receipt history before pointing any workflow at it. Never test restore with
event flags; use a synthetic ledger fixture. Preserve the original database
until the restored copy is verified.

## Synthetic operations drill — October 1, 2026

`python3 scripts/operations-drill.py` passed all 14 checks on a service bound
only to loopback. The saved result is
`.runtime/operations-drill/run-20261001T225914Z/result.json` (ignored and
private). It recorded three health observations in each of four phases, exact
checker-shaped response matches, source hashes, an SQLite recovery backup, and
startup revision markers and process stop/start intervals. Record A survived candidate restart and
source-only rollback; record B, placed after the change, also survived both.
The final database held two records, and the saved result omits their bodies.

This verifies local fixture persistence and command-sequencing only. The
candidate differs from baseline by a revision marker, so this is not evidence
that an actual security patch preserves event checker behavior. Organizer
responses, Docker deployment, network ingress, flag expiry and event rollback
remain unverified. Use the drill output as synthetic training evidence and
write an event-specific verification record from the workspace template.

## Tulip replay integration — October 1, 2026

The supplied farm template and Tulip replay were reviewed as code references;
neither was executed or copied into the repository. The farm template's
defaults span a guessed 1–1000 team range, 32 workers, repeated rounds, and
object IDs 2000 down to 1. It prints captured values and submits directly over
a TCP socket without a verified receipt contract. The replay accepts an
arbitrary `--target`, disables TLS certificate checks for HTTPS, and prints the
captured value. These defaults do not meet this harness's published-scope,
private flag handoff or signal-only submission rules.

Added `scripts/tulip-replay.py` as a one-request adapter: the exact target must
match an operator-maintained published-target list; it stores captures in a
private inbox, refuses public plain HTTP, does not follow redirects and has no
submission path. Three local mock-server tests cover exact allowlisting,
private non-echoing handoff and HTTP rejection. No event endpoint was contacted.

## Budget-conscious model selection — October 1, 2026

- The provisional root/worker model is DeepSeek V4.1 Flash. Five native Codex
  agent files explicitly set MiMo V2.6 Pro for audit/code review/defense, MiMo
  V2.6 Flash for PoC development, and DeepSeek V4.1 Flash for verification.
  Other agents inherit the selected model. The assignment is a cost/latency
  hypothesis, not an A/B winner.
- `bin/ctf-codex models --zdr` returned eligible endpoint metadata for DeepSeek
  V4.1 Flash (27 endpoints), MiMo V2.6 Flash (3), MiMo V2.6 Pro (1), GLM 5.3
  Flash (28), GPT-6 Luna (3) and GPT-6.1 Sol (3). The diagnostic expressly
  warns that endpoint eligibility does not confirm account/key enforcement.
- A native Codex patch task against the synthetic fixture received OpenRouter
  HTTP 402 before inference because the account has never purchased credits. A
  free Qwen 3.8 27B attempt returned HTTP 429 before inference. Neither attempt
  incurred cost or yielded a model result. OpenRouter's key metadata reports a
  $1 limit, but the balance cannot make a paid request until credits are bought.
- A fresh read-only metadata check still reports free-tier status, a $1 limit,
  $1 remaining and $0 usage. The account therefore cannot provide paid A/B
  evidence yet; no new inference was attempted.
- `python3 -m unittest discover -s tests -v`: 50 tests passed after the current
  reliability, Python-preflight, operations-drill and Tulip-adapter changes.
  Shell syntax, Python compilation and
  `git diff --check` passed. `bin/ctf-codex doctor` passed strict config for all
  seven profiles, discovered 12 agents and 15 skills, and performed no
  inference. The latest native doctor reported 22 ok, 1 idle, 1 note and 1
  warning: noninteractive `TERM=dumb`; it reported 0 failures.
- Synthetic comparison fixtures are tracked under `benchmarks/model-selection/`;
  all attempted event logs and metadata remain in ignored `.runtime/`.
