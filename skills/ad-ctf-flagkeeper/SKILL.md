---
name: ad-ctf-flagkeeper
description: Maintain a private deduplicated A/D flag ledger and configure the authorized automatic flag submitter.
---

# Flagkeeper

Own the flag ledger, adapter and submission receipts. Do not audit services or
change patches except to help producers integrate local import files. Read
organizer event details and actual submission API documentation. Never guess
URLs, auth, payloads, status labels or batch limits.
Earlier submission earns more points. Prioritize configuring the documented
local submitter before captures arrive, and monitor its queue and receipts for
delays. Do not bypass the configured submitter or published rate limits.

Use `scripts/flag-ledger.py` from the repository root (the coordinator provides
its absolute path). Store everything under ignored `.runtime/flags/`. Producers
write a complete temporary file, then atomically rename it to
`.runtime/flags/inbox/<unique-name>.jsonl`; never put flags in arguments,
messages or model-visible stdout. Import files contain `flag`, `service`, `team`,
`flag_id`, `expires_at` (timezone-aware ISO timestamp from published metadata),
and `source`. The launcher watches this directory once per second, imports files,
and submits pending flags immediately when the private organizer API config is
present. Unknown expiry does not delay an immediate submission. The ledger
deduplicates and retains provenance; logs contain counts and hashed IDs only.
Imported files move under `.runtime/flags/imported/`; malformed files move to
`.runtime/flags/rejected/` for private review.

Use `status` and `plan` to report counts, earliest expiry and flags at risk.
Never infer an expiry time. The automatic submitter sends unknown-expiry flags
immediately and checks known expiry before sending.

After an ambiguous send or timeout, use `review` to list only hashed IDs, state,
expiry, attempts and receipt counts. Use `receipts --id <sha256>` to inspect
recorded reconciliation history. These commands never print flag values. Check
the official receipt source locally, then reconcile with JSONL containing the
hashed `id`, normalized `status`, and a private evidence reference. Reconciliation
stores that reference so later operators can audit the decision.

Configure `.runtime/flags/submission.json` and the generic
`scripts/submit-http.py` only if its JSON contract matches the published API.
Otherwise set `CTF_SUBMISSION_ADAPTER` to a private adapter built against that
API. It must implement `--check` as a local-only config validation with no
network calls. The adapter takes a JSON object with `flags` (entries containing hashed `id` and actual
`flag`) on stdin, returns `results` with `id` and normalized `status`. Allowed
statuses: `accepted`, `duplicate`, `rejected`, `expired`, `retry`, `uncertain`.
Match every result to its input; unexpected/missing results are uncertain.
Never log raw request/response bodies or bearer credentials. Test using mocks
for duplicate, expiry, partial response, auth failure, rate limits and timeout.

The launcher starts the automatic submitter only when the private config exists,
after Codex setup. It is tied to the Codex process. The submitter polls once per
second and flushes pending flags in bounded batches, earliest expiry first.
Treat timeouts and crashes after send as uncertain; never blindly resend them.
Stop on adapter errors or rate limits, preserve the queue and report counts.
Acceptance is based on documented receipts, never HTTP 200 alone. This scoped
submitter is the only component permitted to contact the configured flag API.
