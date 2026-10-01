---
name: ad-ctf-inventory
description: Map A/D Docker services, languages, storage, reverse-proxy ingress, flag IDs and checker behavior into service manifests and a prioritized ownership board.
---

# Inventory and checker contract

Inventory only supplied source, own VM and documented interfaces. For each
service record language/framework from manifests and entrypoints, source hash,
image digest, Dockerfile/Compose project, listeners, ingress proxy, mounts and
named volumes, process user, dependencies and database type. Docker is expected
from the PDF; Compose, web frameworks and databases must be discovered.
Never print unrestricted `docker inspect`, `compose config` or environment
dumps; they may expose credentials. Use bounded fields and private evidence.

Map ordinary user flows, checker-like create/retrieve, public flag ID meaning,
flag storage and published expiry. Populate a service.toml per service, retain
unknowns and label assumptions. No port scanning outside listed services.
Check own Docker/Compose, WireGuard reachability, SSH and capture tools as
administrative dependencies; those utilities are not attack targets.

Prioritize active flag exposure, reachable shared root causes, missing uptime
baselines and quick defensible fixes. Give audit source/flag paths, traffic the
service port/time window, defense persistence/rollback details and flagkeeper
API documentation/flag metadata paths. Document gaps in your own handoff and
send the coordinator service ownership proposals. Keep secret source and event
facts inside ignored workspaces; tracked skills remain generic.

