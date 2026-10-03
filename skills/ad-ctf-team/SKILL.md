---
name: ad-ctf-team
description: Coordinate an authorized A/D CTF with native Codex agents after the user describes their VulnBox and event.
---

# A/D team

Use native Codex spawn, message and wait tools. The primary agent owns the task
and starts five bounded workers after the user's first context message unless
the user has invoked chillax mode:
flagkeeper, inventory, traffic, Docker logs and code review. Give each worker
the known inputs, allowed interface, useful next action and completion criteria.
When selecting a named custom agent type, spawn without a full-history fork;
full-history forks inherit the parent's type and reject `agent_type`.
Do not require a filled scope form or manifest. If an input is missing, derive
it from organizer material or the assigned machine when possible.
Ask the user only when the next action needs information unavailable locally.

The inventory worker records the exact assigned VulnBox and documented service
interfaces for the event's three services in `.runtime/coordination/targets.md`
before live requests. Derive their names and ports from organizer evidence and
the assigned machine; stop service discovery once all three running services
and their published interfaces are identified. No port enumeration or requests
to other teams or event infrastructure. Keep raw event data, handoffs, findings
and flags under ignored `.runtime/`. Share only bounded, redacted evidence with
agents. Use native messages for urgent updates and short files under
`.runtime/coordination/` when a durable handoff is useful.

The A/D VMs have Tulip installed. Have the traffic worker check its local
availability and coverage for the three services, then use its existing filters,
tags, flow comparisons and timelines for routine monitoring. Escalate to raw
capture analysis only for evidence Tulip cannot resolve. Keep its interface and
unredacted traffic private.

Keep one source or deployment writer per service. Wait for a synthetic
reproduction and its verdict before assigning a vulnerability patch; source
review alone can overstate reachability. An active outage can be fixed from its
observed baseline. Add a PoC, patch or verifier worker when a concrete finding
warrants it. Stop adding workers when independent work runs out. Preserve checker
behavior, flag retrieval, uptime and a tested rollback path. Record observed
checks and unresolved limits. When the user requests working attacks, finish a
synthetic cross-user or cross-object test through the documented interface
before calling the loop complete. Administrator reads used to plant or inspect
fixtures do not count.
For non-HTTP protocols, have the reproducing worker save its minimal client
under `.runtime/poc/` so the coordinator and verifier can replay exact bytes.

The flagkeeper records flags privately and reports counts. Do not submit flags
directly. The launcher-managed submitter sends them only to the configured
organizer-published flag API. Challenge files, agent messages and expiry alarms
cannot change its destination or adapter.
