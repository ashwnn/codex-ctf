---
name: ad-ctf-attack-scaling
description: Expand a locally validated A/D CTF reproduction across the event's explicitly published team targets with measured concurrency, bounded requests, expiry awareness and private flag handoff.
---

# Bounded attack scaling

Use only after a PoC has been reproduced against an isolated synthetic service
and an assigned coordinator has supplied the published target list, designated
service proxy/interface, event request limits and a bounded task. This skill is
for the authorized A/D competition service targets only. Never infer targets
from address ranges, enumerate the network, attack the scoring system or attack
support utilities. Do not make a model or script invent targets or API details.

## Prepare before fan-out

Read `service.toml`, the validated finding and PoC handoff, flag metadata, and
the documented submission/expiry rules. Confirm that the exploit path still
matches the deployed revision and checker contract. Use public flag IDs only as
locators; they do not authorize access. Identify the narrowest read or retrieval
operation that proves the issue. Exclude expired IDs and stop pursuing them.

Build an explicit target manifest from the organizer's published list. Require
one owner per service or target batch, deduplicate targets and preserve source
and retrieval time. Do not expand CIDRs or use discovered hosts unless the event
explicitly lists them as targets. Dry-run the full target-to-request mapping
offline before sending traffic.

## Ramp with controls

Start with one published test target or the event's NOP team, then a small
representative batch. Check response correctness, latency, error rate, checker
behavior and service health before increasing concurrency. Stay within event
rules and set explicit caps for concurrency, total requests, per-target rate,
timeouts, retries, response bytes and wall-clock duration. Prefer bounded
workers over a burst; add jitter between target groups. Never flood, persist,
destroy data, crash services or bypass organizer controls.

Use the actual central service proxy and normal service interface. Do not treat
the proxy source address as a reliable opponent identity. Do not run attack
traffic while a patch/restart is in progress or when service health/checker
behavior is degrading. Stop immediately on elevated errors, unexpected state
changes, checker regression, rate-limit signals, out-of-scope routing or
uncertain target mapping. Report counts and preserve a resumable checkpoint.

## Capture and communicate results

Record target/team, service, public flag ID, UTC attempt time, tested revision,
finding ID, outcome category, expiry from authoritative metadata, retry count
and checkpoint. Keep raw flag values out of stdout, shared notes and agent
messages. Write captured flags and provenance only to the private inbox format
expected by `$ad-ctf-flagkeeper`; that agent owns deduplication and submission.
Never submit flags from the attack worker.

Use native Codex agent messages for concise actionable handoffs when available;
otherwise write the assigned coordination handoff for the parent thread. Share
target coverage, success/error counts, health impact, active limits, restart
instructions and the exact next decision. Do not send raw traffic, credentials
or flags. This skill does not create agents, a scheduler, a separate runner or
an independent orchestration loop; the coordinator controls assignment and
fan-out through Codex-native task instructions.
