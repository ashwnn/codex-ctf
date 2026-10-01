# Checker and service contract — @SERVICE@

Use this as a compact record of observed behavior for this service. Fill it from
published event material, the deployed service, and bounded observations. Keep
unknowns explicit; do not infer a route, target, response, or timing from a
different service. This record supports patch decisions and repeatable checks;
it is not a phase gate.

## Provenance

| Field | Value |
| --- | --- |
| Service / public identifier | Unknown |
| Published scope source and revision | Unknown |
| Deployed source revision / image digest | Unknown |
| Observation window (UTC) | Unknown |
| Observer and workspace revision | Unknown |
| Evidence references | Unknown |

## Normal service flows

Record the smallest ordinary user and checker-like flows that represent healthy
service behavior. Redact credentials and flag values; use synthetic flags in
local verification.

| Flow | Preconditions | Request sequence / input shape | Expected response shape | State change / persistence | Evidence |
| --- | --- | --- | --- | --- | --- |
| Health / landing page | Unknown | Unknown | Unknown | Unknown | Unknown |
| Create or place object | Unknown | Unknown | Unknown | Unknown | Unknown |
| Read or retrieve object | Unknown | Unknown | Unknown | Unknown | Unknown |
| Update / delete, if supported | Unknown | Unknown | Unknown | Unknown | Unknown |
| Invalid or missing identifier | Unknown | Unknown | Unknown | Unknown | Unknown |
| Unauthorized cross-owner access | Synthetic identities only | Unknown | Unknown | No unauthorized state change expected | Unknown |

## Flag lifecycle

| Stage | Published behavior | Observation / evidence |
| --- | --- | --- |
| Placement cadence and ownership | Unknown | Unknown |
| Public flag identifier meaning | Unknown | Unknown |
| Storage location and isolation | Unknown | Unknown |
| Retrieval path and authorization | Unknown | Unknown |
| Expiry and refresh behavior | Unknown | Unknown |
| Persistence across restart | Unknown | Unknown |

## Response and availability details

- Exact status codes, headers, and response fields the checker relies on:
  Unknown
- Retry, timeout, ordering, and idempotency behavior:
  Unknown
- Known health signal and how it is observed:
  Unknown
- Baseline latency/error measurements and sample window:
  Unknown
- Checker cadence and next observable check, if published:
  Unknown
- Unresolved questions or competing observations:
  Unknown

## Change notes

Append dated, evidence-linked corrections here. Preserve the previous value and
explain why the new observation supersedes it.
