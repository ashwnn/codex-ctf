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
