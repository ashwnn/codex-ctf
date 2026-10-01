---
name: ad-ctf-traffic-triage
description: Quickly identify actionable anomalies in own-service A/D CTF traffic, Docker/application logs and checker baselines, then route evidence into a causal reconstruction.
---

# Focused traffic triage

Use this as the quick monitor-to-handoff workflow. For packet reconstruction,
protocol quirks and causal testing, continue with
`$ad-ctf-traffic-reconstruction`. Use only captures and logs from the team's own
service or evidence the event explicitly authorizes. A shared proxy address is
not an opponent identity. Keep raw captures, bodies, credentials and flags in
the ignored workspace.

## Detect and classify

- Establish the healthy/checker baseline: request cadence, route/method,
  response code/length, latency, create/read behavior, retries and expected
  egress. Use the event's actual tick timing and published service interface.
- Inspect bounded windows. Group flows by time, service, route, size, response,
  state change, error/restart and egress. Correlate own-service PCAP indices
  with proxy/application/Docker logs and storage changes; account for NAT,
  retries, clock offsets and encrypted/truncated payloads.
- Classify each signal as normal/checker, noise, probe, suspected exploit or
  demonstrated exploit. A strange path, client fingerprint, 4xx/5xx, burst or
  flag-shaped output by itself is not proof.
- Select the smallest useful evidence slice. Preserve raw bytes locally and
  prepare a reviewed, redacted excerpt with source offsets, UTC times, stream or
  request IDs and limitations before sharing it with another agent.

## Escalate with a useful handoff

For an actionable lead, give the parent thread and relevant audit/PoC workers:
service and deployed revision; UTC window; request/stream identifiers; baseline
comparison; observed status, state change or egress; evidence locations; what is
observed versus inferred; plausible benign explanation; confidence; next
discriminating test; urgency and owner. Reuse the same finding ID across
handoffs. Send findings with code-path questions to `$ad-ctf-service-audit`,
runtime failures to `$ad-ctf-docker-log-triage`, and confirmed exploit hypotheses
to `$ad-ctf-poc-development` for isolated synthetic reproduction.

Never send raw flags, credentials or unreviewed traffic excerpts. Do not live-test
crashes or disruptive payloads. Stop and notify the coordinator if service
health or checker behavior degrades; do not independently patch or attack peers.
