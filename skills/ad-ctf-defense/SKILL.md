---
name: ad-ctf-defense
description: Protect A/D uptime with minimal service patches, Docker persistence awareness, checker regression testing and explicit rollback.
---

# Defense and uptime

Read the actual service evidence, deployed revision and finding record. Obtain
single-writer assignment before edits. Preserve backups, hashes, container image,
mounts, named volumes, run user, limits and a service-specific rollback command.
Back up the files being changed and any data a migration touches; avoid copying
entire build trees or volumes for a one-file patch.
Read compose configuration locally without exposing expanded secret environment.
Never use broad `compose down`, `down -v`, volume prune or database resets as a
patching shortcut. Patch the authoritative source/image, not an ephemeral layer
that disappears on recreation. Rebuild/recreate only the relevant service after
testing. The current request authorizes fixes on the assigned offline VulnBox;
use native sandbox controls and record every deployed change.

Use $ad-ctf-service-audit to tie the fix to a confirmed root cause. Confirm the
reproduction verdict before changing the deployed service; keep unconfirmed
hardening separate from exploit fixes. Prepare a
synthetic baseline covering normal create/read/update, authorization boundaries,
flag placement/retrieval, exact UI/response shapes, older live flags, persistence
and service restart. Include the original reproduction and alternate encodings.
If a retention reaper can expire the fixture during rebuild, create fresh
synthetic records after restart and prove the owner's positive control before
interpreting an attacker denial.
Use the service database's clock for fixture timestamps; host and VM clocks may
differ enough for a reaper to delete fresh-looking host-side rows.
Save the baseline in `verification/<service>-baseline.md` with the tested
revision, exact inputs, expected and observed responses, restart behavior and
the source of each checker expectation. If organizer checker scripts are
available, run them on an isolated copy; otherwise label synthetic flows as
proxies for checker behavior. Reuse this baseline for every patch comparison.
A local healthcheck is weaker evidence than the organizer's checker. Do not
claim checker compatibility without checker results. Record latency/error delta
and test limits. Revert quickly on observed checker regression using the saved
rollback; data rollback must not overwrite newly placed flags.

Classify outages as container/process, resource, dependency, ingress or functional
checker failures. Investigate one service first; do not block all traffic or
create restrictions that prevent legitimate checker behavior. Share actionable
evidence with audit/traffic and coordinator, and record applied revision plus
verification in the shared finding. No phase gates or automatic reviewer.

Use $ad-ctf-deployment when the event requires immutable promotion or operator
notices. The offline VM has no live leaderboard checker. Record local checker-like
results as local evidence, and do not claim official checker validity.
