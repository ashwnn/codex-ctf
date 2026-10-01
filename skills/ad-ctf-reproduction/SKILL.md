---
name: ad-ctf-reproduction
description: Build and validate a bounded A/D service reproduction against a local synthetic copy and explicitly authorized published service targets, with private flag handoff.
---

# Reproduction and runner

Start from a finding supported by source or own-service traffic. Reproduce on an
isolated copy with synthetic flags first; preserve normal application behavior
and state. Read service.toml for explicit allowed service proxy, port/directory,
team IDs and authorization. No direct peer VM access or attacks on utilities,
VPN, scoring infrastructure, SSH, Tulip or the submission endpoint. Normal API
flag submission is a distinct flagkeeper task. NOP team 1 is a published test
target, not blanket authorization for unknown network addresses.

Save a per-service script in the ignored workspace; parametrize only documented
team targets and public flag IDs. Bound concurrency, timeouts, total requests,
retry count, response size and delays to event limits. Avoid unbounded scans,
state deletion, crashes, flag modification and floods. Prefer read-only retrieval
or minimal service interactions needed for the validated root cause. Respect
actual published expiry and stop attempts for expired IDs.

Write captured values and provenance to private `flags/inbox/` JSONL files for
the flagkeeper. Never print flags, send them to agents or submit independently.
Separate target discovery from attack logic, and record success/error counts,
finding ID, tested revision, validity window and restart instructions. A tool
match is not a validated reproduction. Report unavailable live inputs and keep
local verification useful without inventing any service or API contract.

