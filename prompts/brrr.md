# /brrr: A/D CTF surge

Use the native Codex multi-agent tools now. This is an explicit request to
surge the authorized A/D CTF work already described in this workspace. Read
`AGENTS.md`, `team.toml`, service manifests and current coordination handoffs
first. Stay within the event's published team/service scope and published rate
limits. If scope or rules are not available, work on local source, logs,
captures and checker evidence while asking the coordinator for the missing
published scope; do not guess targets.

Keep the primary thread as coordinator and preserve the dedicated flagkeeper.
Start the existing five roles if they are not already active: flagkeeper,
traffic reconstruction, Docker/service inventory and logs, code/security
review, and PoC reproduction/development. Reuse the configured native agent
profiles where their descriptions match. Then scale toward twenty concurrent
agents only while there are distinct, useful, unowned tasks. Split work by
service or independent hypothesis; avoid duplicate probes and keep one writer
per service. Use shared role inbox files for worker-to-worker communication;
the primary relays urgent messages using native agent tools. Direct sibling
messages were unavailable in a synthetic CLI test. Record sanitized handoffs
under `coordination/` so findings survive
turn boundaries.

Prioritize checker behavior, service uptime, flag lifecycle and safe rollback.
For each exploit hypothesis, ask a PoC worker to establish a minimal local or
explicitly in-scope reproduction before assigning bounded validation to other
teams. Use only the lowest request rate that validates the PoC within event
rules; stop on instability, checker impact, unexpected scope or rate-limit
signals. Do not run broad scans, destructive payloads, denial-of-service,
credential attacks, or unbounded mass exploitation. Report the exact scope,
evidence, confidence, and rate used before scaling a validated technique.

The flagkeeper records recovered flags only in the private ignored ledger and
holds every submission until the user gives a current explicit signal. Never
print flag values in messages or handoffs. Scale down when independent backlog
is exhausted, keep the flagkeeper active, and report active roles, task
ownership, validated PoCs, service health and blockers to the primary thread.
