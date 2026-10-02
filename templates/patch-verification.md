# Patch verification record — @SERVICE@

Create one copy per proposed or applied change. Record what was actually run;
`not run` is a valid result. A local health response alone does not establish
checker compatibility. Use synthetic flag values and a disposable service copy
where feasible. This record is evidence, not an automatic approval gate.

## Change identity

| Field | Value |
| --- | --- |
| Finding ID and owner | Unknown |
| Writer / deployment owner | Unknown |
| Started / completed (UTC) | Unknown |
| Pre-change source revision | Unknown |
| Candidate source revision | Unknown |
| Image / binary digest before and after | Unknown |
| Patch and test evidence paths | Unknown |
| Stable deployment checkpoint and artifact digest | Unknown |
| Local deployment check evidence ID | Unknown |
| Human external observation: exact revision, up/down/unknown, UTC time/tick | Unknown |
| Shared-state or flag-store backup reference | Unknown |

## Baseline and candidate comparison

Use the same inputs on the baseline and candidate when practical. Include the
original reported behavior and normal checker flows. Record latency/error
measurements with the sample size and window; do not invent pass thresholds.

| Check | Baseline result | Candidate result | Evidence / limits |
| --- | --- | --- | --- |
| Service starts and stays healthy | Not run | Not run | Unknown |
| Ordinary create / place flow | Not run | Not run | Unknown |
| Ordinary read / retrieve flow | Not run | Not run | Unknown |
| Cross-owner access control | Not run | Not run | Synthetic identities only |
| Original reproduction / exploit | Not run | Not run | Synthetic data only |
| Alternate representation or state | Not run | Not run | Unknown |
| Retrieval of pre-patch stored flags | Not run | Not run | Verify persistence without recording flag values |
| Flag placement, retrieval, expiry | Not run | Not run | No real flag values in this record |
| Restart and persistent state | Not run | Not run | Unknown |
| Checker result / response compatibility | Not run | Not run | Unknown; do not claim without evidence |
| Latency, errors, resource use | Not run | Not run | Include sample size and observation window |

## Rollout and rollback record

- Planned change and operator-controlled command:
  Unknown
- Writer coordination and competing changes checked:
  Unknown
- Rollback procedure and preconditions:
  Unknown
- Rollback artifact/revision verified before change:
  Unknown
- How rollback preserves newly placed flags and persistent data:
  Unknown
- Monitoring signal, observation window, and event/checker ticks watched:
  Unknown
- Rollback performed? If so, time, result, and evidence:
  Not run
- Predeployment notice and planned maintenance window; human leaderboard watcher:
  Unknown

## Outcome and follow-up

- Patch state: proposed / applied locally / deployed / reverted / unknown
- What the evidence supports:
  Unknown
- Regressions, limits, and unresolved gaps:
  Unknown
- Next useful observation or owner:
  Unknown
