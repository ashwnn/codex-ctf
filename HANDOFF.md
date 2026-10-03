# CTF harness handoff - 2026-10-02

Run `./codex-ctf` from the repository root after exporting `OPENROUTER_API_KEY`.
The native Codex TUI owns the workflow. Give it the known VulnBox and connection
facts. `/prompts:brrrr` expands distinct attack work; `/prompts:chillax` reduces
worker count. The launcher creates no service workspaces or required manifests.
Private sessions and evidence are under ignored `.runtime/`.

## Authorized offline test

The harness used the separate host-only `FAUST2026-Harness` clone at
`192.168.56.104`, with only its documented ports: LAMP 1337, ALF 1986,
IMC 8080 and Rufflecopter 35244. No competition VPN, other team, scoreboard,
real flag or submission was used. All 10 service containers were Up at the
last completed run. The offline image has no official checker or score feed.

The first full loop inventoried and exercised all four services. It deployed
ALF login and malformed-base64 guards and a tar archive guard, then checked
normal translation and upload flows plus rollback. The `brrrr` loop used
synthetic records through the published interfaces. It demonstrated and
patched an IMC cross-user read caused by `null == null`, and a LAMP account
takeover caused by a Redis-only registration check. Both patches passed
vulnerable, patched, rollback and reapplied replay. The harness also confirmed
a native ALF parser overflow and worker crash. That finding is still open.

A focused closeout started ALF parser mitigation and Rufflecopter query-path
review but stopped when OpenRouter returned HTTP 429. The ALF worker began
corpus preparation but saved no usable corpus; no ALF native fix was deployed.
The Rufflecopter worker was
interrupted before an external-port verdict. Continue these two tasks from the
retained sessions and prior handoffs, without repeating the inventory. A
Rufflecopter PostgREST issue is not established through port 35244.

## Provider and accounting

The former free-preview model's daily request limit was exhausted.
OpenRouter reported reset at `2026-10-03 00:00 UTC`. The key has no purchased
credits. The two completed runs used ephemeral sessions, so their native child
usage cannot be recovered exactly. The first run's root used 599,491 tokens;
the `brrrr` root used 5,321,966. The focused closeout retained three sessions,
which together used 398,584 tokens. Observed usage is 6,320,041 tokens;
actual total is higher because the first two runs' child usage is missing.
The launcher now retains sessions for future per-agent accounting.
At the 2026-10-02 catalog price for DeepSeek V4.1 Flash, those observed
input, cache-read and output tokens would cost $0.129718620555. This is a
lower bound, not an exact all-agent bill. OpenRouter reported $0 actual usage
for the former free-preview key.

The TUI initially rejected SQLite migration checksums left by an earlier
Codex build. Its local SQLite files were backed up under ignored
`.runtime/codex/`, then the Ubuntu CLI recreated them. The retained rollout
JSONL files were preserved, and `./codex-ctf` opened successfully with Space
the former default selected.

Do not claim checker success, score or complete challenge compromise from this
offline evidence. Keep all flags held unless the user explicitly authorizes
submission.
