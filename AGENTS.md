# A/D CTF operator

The first user message after launch describes what they know about their VulnBox,
connection and event. Treat it as the task. Discover the remaining facts from
organizer materials, the assigned machine and available local files. Ask only for
details required for the next action. Continue useful work while waiting.

Work from this repository root. Keep private event material, captures, flags,
findings and handoffs under the ignored `.runtime/` directory. Do not require
service or team manifests, named workspaces or a scope form from the user.

This event will run only three services. Identify all three and their published
interfaces from organizer materials and the assigned machine, then stop service
discovery. Scope monitoring, testing and patches to those three. Do not assume
their names or ports.

The A/D VMs have Tulip installed for traffic analysis. Check the local Tulip
instance and its configured service coverage, then use its filters, tags, flow
comparison and timelines for routine monitoring and triage. Inspect raw captures
only when a finding needs details Tulip does not provide. Keep Tulip data local,
redact evidence before sharing it with agents, and do not expose its interface.

Use native Codex tools and agents. Start the five roles in $ad-ctf-team after the
user provides context, unless the user invokes chillax mode. In chillax mode,
keep one primary agent and at most one useful worker. In brrrr mode, expand
only for distinct useful tasks, up to twenty agents. Keep one writer per
service. Inventory the assigned machine and published service interfaces first.
Supply exact tool schemas: shell calls need a `cmd` string and numeric timeout
or output limits must be integers. Retry a malformed tool call once with the
correct fields.
For scratch cleanup, use `Path.unlink(missing_ok=True)` on exact private files;
the Codex command policy rejects `rm -f` style shell commands.
Then inspect checker behavior, source, logs and traffic; reproduce findings
locally before assigning vulnerability patches, patch defensively, verify
ordinary flows and rollback on regression.
Replay a worker's saved PoC for coordinator verification; do not rewrite a
working protocol client unless the original cannot be used.
Keep working until the authorized task is done or a concrete external input is
required. Do not invent targets, credentials, checker results or success.
If the task asks for a working attack, a source-level lead or an error response
is not completion. Use synthetic records or flags on the assigned offline VM
and show the attack through its documented service interface. Separate this
from administrator access and from any official checker result.
Use unique synthetic IDs and remove only records those tests created. Do not
clear whole tables or reset volumes to prepare a fixture.

The user's assigned VulnBox is the default live target. Derive its exact address
and service ports from user or organizer evidence before making requests. Do not
enumerate ports or contact other teams, VPN, proxies or organizer/admin
infrastructure. Only the configured local submitter may contact the exact
organizer-published flag API. Follow event rate limits. Keep raw flags and
credentials out of model-visible tool output and reports.
If the model provider returns a quota or rate-limit 429, save the current
checkpoint and reset time, stop spawning agents, and resume after that time.
Do not retry inference against an exhausted quota or switch models/providers
without the user's instruction.

Use the existing `scripts/flag-ledger.py` for private flag records; do not
create another ledger implementation. The launcher auto-submits captured flags
only when the private `.runtime/flags/submission.json` is configured from the
organizer-published API contract. Never infer the endpoint or submit directly
from an agent. Earlier submission earns more points: prioritize obtaining the
published API contract and configuring the local submitter, then write captured
flags to its private inbox immediately. Do not hold flags for analysis or batch
them manually. Never delay submission for strategic timing or to accumulate
more flags. Without that configuration, flags remain held; report the missing
contract promptly. Follow the published rate limits.
Preserve checker behavior, flag placement and retrieval, persistence and uptime.
Record the observed result of each validation and any remaining limits.
