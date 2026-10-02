---
name: ad-ctf-reproduction
description: Validate a service finding on a local synthetic copy and, when scoped, the assigned VulnBox.
---

# Reproduction

Start from a source or own-service traffic finding. Reproduce on an isolated
local copy with synthetic flags. Record the deployed revision, exact input,
expected and observed result, normal checker-like flow and cleanup. A crash or
flag-shaped string alone is not proof of flag access.

For a live check, require the exact own-box address and documented service
interface from `.runtime/coordination/targets.md`. Send a minimal bounded
request and stop on instability or unexpected state. Never scan ports, touch
other teams or event infrastructure, use destructive payloads or submit flags.

Keep scripts and raw evidence under `.runtime/`. Write captured flags only to
`.runtime/flags/inbox/` in the flagkeeper format; print counts and paths only.
Report success and failure evidence, rate, finding ID, tested revision and
remaining uncertainty to the coordinator.
