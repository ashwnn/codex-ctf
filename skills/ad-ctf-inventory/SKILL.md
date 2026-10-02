---
name: ad-ctf-inventory
description: Establish the assigned VulnBox and checker baseline from user and organizer evidence without scanning.
---

# Inventory

Use the user's first message, organizer materials and own-box configuration to
record the exact assigned address and documented service interfaces in
`.runtime/coordination/targets.md`. Do not derive targets from address patterns,
traffic, DNS or neighboring machines. Do not enumerate ports or contact other
teams or event infrastructure. If the address or port is unknown, work on
available local source and logs and ask for the missing fact.

For each service, record the deployed revision, entrypoint, documented port,
container, persistent storage, process user, checker-like create and retrieve
flows, flag store and rollback path. Read bounded Docker fields and logs; do
not dump environment variables or credentials. Compare local source with the
running revision before treating a source finding as live. Save private evidence
under `.runtime/`, and give the coordinator concise ownership proposals and
unknowns.
