---
name: ad-ctf-brrr
description: Explicit A/D surge that expands a native Codex team toward twenty workers for PoC discovery, validation and partitioned authorized attack tasks.
---

# A/D surge

Use only after the user explicitly invokes `/brrr`, `/prompts:brrr`, the `brrr`
launcher command or equivalent direct instruction. The primary reads the roster,
board, service manifests, actual published target list, flag IDs and validated
findings. Prioritize offense while retaining the dedicated flagkeeper and
critical checker uptime owner. This is native Codex delegation: use only the
agent spawn, message, wait, resume and close tools. No shell agent scheduler.

Aim for twenty total child agents when there are twenty independent useful
tasks. Suggested capacity: 1 flagkeeper, 1 traffic, 1 Docker logs, 3 code
review, 1 patch/uptime, 4 PoC developers, 2 PoC testers and 7 attack workers.
Adjust to the real service count and evidence. Reuse running workers. If fewer
useful tasks exist, give the actual count and needed inputs; do not invent
targets or idle roles just to reach twenty.

Each worker receives a bounded service or trust boundary, input paths, permitted
network interface, output path, agent IDs of peers and completion criteria.
The coordinator partitions attack work into disjoint `(service, team)` shards;
never have two workers send the same exploit to the same team and service.
Exclude the own team, undocumented targets and out-of-scope infrastructure.
Only a locally validated PoC revision reaches attack agents; a NOP team check
uses the published reverse proxy when available. Distribute script revision,
flag ID window and request limits in the assignment. Scale attack agents by
target shards, not by increasing simultaneous requests against one service.

Workers use recipient inbox files and the primary's native relay when evidence
changes another role's work; follow
[communication.md](../ad-ctf-team/references/communication.md).
Traffic/logs send likely exploit paths to code review and PoC developers;
PoC developers send validated revisions to testers and attack agents; testers
send failures and success criteria back; attack agents send counts, latency and
error trends to PoC developers and the primary; patch owners receive checker
or exploit regressions. Every worker saves a concise private handoff. Native
Messages never contain raw flags, secrets or unredacted traffic. Direct native
sibling messaging was unavailable in a synthetic Codex CLI test.

Flag capture goes to private `flags/inbox/` files for the flagkeeper. It imports
and holds flags; `/brrr` does not signal submission. Published five-tick expiry
still applies, and the primary reports likely loss from holding until event end.
Do not run unbounded scans, service crashes, deletion, flag modification or
traffic floods. If a target becomes unstable or rate limited, back off and
message the critical uptime owner and primary. Preserve one code/deployment
writer per service and the checker regression process.
