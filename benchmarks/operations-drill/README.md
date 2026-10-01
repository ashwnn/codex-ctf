# Synthetic operations drill

Run this local diagnostic before competition to rehearse checker-shaped
responses, persistent records, service restarts and source rollback without
event targets, credentials, real flags or model calls:

```bash
python3 scripts/operations-drill.py
```

It binds only to `127.0.0.1` on an ephemeral port. It creates a dated private
run under ignored `.runtime/operations-drill/` with source hashes, a SQLite
recovery backup, phase start/stop times, three health observations per phase,
expected-response checks and a `result.json`. The synthetic record bodies are
omitted from that result.

The sequence places A on baseline source, backs up the database, starts the
candidate against the same database, places B after the change, restarts the
candidate, then restores the baseline **source only** while retaining the live
database. A and B must both remain retrievable after source rollback. The
planned stop/start intervals are recorded separately; the diagnostic makes no
claim of uninterrupted uptime. It does not restore the earlier recovery backup
during the rollback test, because doing so would erase the evidence that B
survived.

Codex can launch the diagnostic with its native shell tool and write a dated
copy of `templates/patch-verification.md` referencing the output. Record the
checker contract for this fixture as: health is `200 {service: synthetic,
status: ok}`; owner retrieval is `200 {id, body}`; missing and cross-owner
retrievals are identical `404 {error: not found}`; a placed record persists in
SQLite across service restart and source rollback. These are local fixture
contracts only. Organizer checker behavior, Docker deployment, remote ingress,
event-specific flag placement/expiry, and rollback commands remain unverified.
