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

### Replaying a Tulip request

Treat a copied Tulip request as evidence for one observed flow, not as a ready
target list or a farm runner. Keep the original capture in ignored
`evidence/raw/`; derive a redacted request template and replace only the
documented host and public flag-ID fields. Reproduce it against the local
synthetic service first. For an authorized remote check, select one exact
published service proxy and one current flag ID from the workspace contract.
Do not sweep guessed team subnets or object-ID ranges, fan out across teams,
run a perpetual round loop, or replay state-changing requests outside the
published checker flow. Keep the captured request, cookie, and response body
out of model-visible output.

Do not copy the supplied `exploit-web-template.py` or `tulip_replay.py` into an
event workspace unchanged: their current defaults include guessed broad target
ranges, 32 concurrent workers, repeated rounds, disabled TLS verification,
and raw flag output. The farm template can also send flags directly over a TCP
socket without an event-specific receipt contract. Separate any validated
single-target PoC from the flagkeeper: write captured values and provenance to
private `flags/inbox/` JSONL; print counts and paths only. The flagkeeper alone
handles the held ledger and the user's explicit submission signal.

For a reviewed raw HTTP request, `scripts/tulip-replay.py` provides a bounded
single-request runner. Its `--target` must exactly match one URL in the
operator-maintained `--published-targets` file. It requires one current public
flag ID, caps request/response sizes and timeout, refuses public plain HTTP,
does not follow redirects, writes results to private `flags/inbox/`, and never
submits or prints captured values. Run it from the service workspace. The
allowlist must be populated from published event scope; the script cannot
establish that a user-provided target is authorized.

Write captured values and provenance to private `flags/inbox/` JSONL files for
the flagkeeper. Never print flags, send them to agents or submit independently.
Separate target discovery from attack logic, and record success/error counts,
finding ID, tested revision, validity window and restart instructions. A tool
match is not a validated reproduction. Report unavailable live inputs and keep
local verification useful without inventing any service or API contract.
