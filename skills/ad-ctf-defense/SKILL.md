---
name: ad-ctf-defense
description: Protect A/D uptime with minimal service patches, Docker persistence awareness, checker regression testing and explicit rollback.
---

# Defense and uptime

Read the actual service manifest, deployed revision and finding record. Obtain
single-writer assignment before edits. Preserve backups, hashes, container image,
mounts, named volumes, run user, limits and a service-specific rollback command.
Read compose configuration locally without exposing expanded secret environment.
Never use broad `compose down`, `down -v`, volume prune or database resets as a
patching shortcut. Patch the authoritative source/image, not an ephemeral layer
that disappears on recreation. Rebuild/recreate only the relevant service after
testing; deployments follow the user's live authorization and native sandbox.

Use $ad-ctf-service-audit to tie the fix to a confirmed root cause. Prepare a
synthetic baseline covering normal create/read/update, authorization boundaries,
flag placement/retrieval, exact UI/response shapes, older live flags, persistence
and service restart. Include the original reproduction and alternate encodings.
A local healthcheck is weaker evidence than the organizer's checker. Do not
claim checker compatibility without checker results. Record latency/error delta
and test limits. Revert quickly on observed checker regression using the saved
rollback; data rollback must not overwrite newly placed flags.

Classify outages as container/process, resource, dependency, ingress or functional
checker failures. Investigate one service first; do not block all traffic or
create restrictions that prevent legitimate checker behavior. Share actionable
evidence with audit/traffic and coordinator, and record applied revision plus
verification in the shared finding. No phase gates or automatic reviewer.

