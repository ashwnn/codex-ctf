---
name: ad-ctf-attack-scaling
description: Run validated bounded A/D PoCs against the user's assigned VulnBox while preserving service health.
---

# Bounded attack scaling

Require a coordinator assignment, locally validated PoC, exact documented
own-box interface, event rate limits and a finite request budget. Never invent
or scan targets, contact other teams or event infrastructure, or submit flags
directly. The launcher-managed submitter handles captured flags.
Confirm the deployed revision and checker flow before live requests.

Start with one request. Check correctness, latency, errors and service health
before a small controlled increase. Cap concurrency, total requests, timeout,
retries, response bytes and duration. Stop on instability, rate limits, checker
regression or uncertain scope. Preserve the exact PoC revision and counts.

Write captured flags only to `.runtime/flags/inbox/` for the flagkeeper. Share
counts and redacted evidence with the coordinator. The coordinator controls
agent fan-out through native Codex tools; this skill adds no scheduler.
