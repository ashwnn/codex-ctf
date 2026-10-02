---
name: ad-ctf-poc-development
description: Turn authorized A/D CTF source, binary, configuration and own-service traffic evidence into a minimal, reproducible proof of concept using synthetic data and a local isolated service.
---

# PoC development

Build the smallest artifact that distinguishes a real vulnerability from a
plausible code-level idea. Use only the assigned service, its own supplied
artifacts and explicitly published interfaces. Start offline; use a disposable
local instance and synthetic flags or object identifiers. Do not target other
teams from this development workflow. Keep real flags, credentials, private
source, packet bodies and findings inside ignored `.runtime/`.

## Work from evidence

Read the service evidence, checker contract, deployment inventory and shared
finding record. Confirm the deployed source/image/binary matches the reviewed
artifact and identify the exact entry point, transformations, checks, sink and
expected observable effect. For binaries, record architecture, build identity,
symbols/mitigations and the relevant disassembly or dynamic trace. For
configuration, identify which setting is loaded by the actual boot path. Avoid
assuming a backup source tree or stale image is deployed.

Use a short hypothesis: attacker-controlled input, violated invariant,
preconditions, affected synthetic object, and predicted safe/vulnerable result.
Capture an ordinary successful baseline first. A scanner hit, suspicious log,
crash, or unreferenced unsafe function is only a lead until a controlled test
demonstrates the impact.

## Make the PoC minimal and safe

- Change one input property at a time; preserve exact bytes, encoding, request
  order and required authentication context.
- Use a local-only endpoint or loopback binding. Keep concurrency at one,
  request count low, timeouts short and response capture bounded.
- Use synthetic .runtime/flags/records and test both authorized and unauthorized
  principals where relevant. Do not extract or disclose real flags.
- Prefer read-only proof of access. Do not delete or mutate service data, crash
  processes, create persistence, evade monitoring, or trigger egress.
- Include cleanup and an isolated reset path that does not touch shared volumes.

The PoC should have an exact invocation, required local fixture, expected
vulnerable observation and expected safe observation. Avoid hard-coded event
addresses, guessed API endpoints, secrets, team credentials and broad scans.
Store executable artifacts and private evidence only in the ignored .runtime/ directory;
tracked skill files must stay generic.

## Validate and hand off

Ask the reproduction/test owner to run the PoC against the isolated copy and
compare it with the known-good baseline. The test owner records deployed
revision, fixture, result, checker-like regression status, limits and unresolved
gaps. A useful PoC proves the causal chain and can fail when the vulnerable
condition is removed. A test failure caused by setup uncertainty does not
disprove the vulnerability.

Send the coordinator and relevant audit/traffic/defense workers the finding ID,
artifact location, invocation, preconditions, synthetic result, observed versus
inferred steps, safety bounds, and next step. Coordinate edits through the
assigned single writer. Never put flag values in agent messages or logs.
