# CTF harness handoff

Status: pre-event harness is substantially assembled and locally verified. The
repository keeps Codex as the agent/tool loop, uses the isolated OpenRouter
provider configuration, and contains no separate model router or orchestration
service. No live event target, checker or submission API has been exercised.

## What is ready

- Native Codex team, profiles, custom roles, prompts and skills live under the
  isolated runtime `CODEX_HOME`. Root and role model choices are editable
  hypotheses in `docs/model-selection.md`.
- `bin/ctf-codex doctor` checks Python 3.9+, installs changed files atomically,
  and validates all seven profiles with `--strict-config`. Project-config
  sanitation applies only to the workspace being launched.
- Service initialization creates checker-contract and patch-verification
  templates. Event-specific scope, service revision, flag lifecycle, API
  contract and rollback values must come from published event material and
  observations; leave unsupported facts unknown.
- The private flag ledger supports expiry planning, explicit signal-only
  submission, uncertain receipt reconciliation, and SQLite online backup.
- `scripts/operations-drill.py` exercises a loopback-only service through
  placement, restart and source-only rollback. The verified synthetic result
  is under ignored `.runtime/operations-drill/run-20261001T225914Z/`.
- `scripts/tulip-replay.py` is a one-request adapter for a reviewed raw HTTP
  request. It requires an exact URL match in an operator-maintained published
  target list and writes captured values privately to `flags/inbox/`; it does
  not print flags or submit them.
- Synthetic model-comparison fixtures and instructions are in
  `benchmarks/model-selection/`.

## Verification completed

- `python3 -m unittest discover -s tests -v`: 50 passed.
- `bash -n bin/ctf-codex codex-ctf bin/openrouter-token`, Python compilation,
  and `git diff --check`: passed.
- `bin/ctf-codex doctor`: all seven profiles passed strict-config and native
  prompt/skill discovery; 12 agents and 15 skills were installed. No inference
  was performed.
- Synthetic operations drill: 14/14 checks passed, including that record B,
  placed after the candidate change, survived service restart and source-only
  rollback.
- Tulip adapter mock tests verified one allowlisted request, private inbox
  output, no flag in terminal output, and refusal of unlisted/public-HTTP
  targets. No event endpoint was contacted.

## Model evaluation and spending

The planned personal ceiling is approximately **$60 total**: $5 for evaluation,
$40 for routine competition work, $10 for hard-task escalation, and $5 reserve.
This is a planning allocation; it is not enforced by the harness. Set the
OpenRouter key limit to the remaining budget before paid trials or competition
use.

As of the last read-only key check on 2026-10-01, OpenRouter reported free-tier
status, a $1 key limit, $1 remaining, and $0 usage. An earlier paid DeepSeek
request returned 402 before inference. Therefore no paid A/B winner exists.
Assignments remain provisional. Current ZDR endpoint catalog data makes GLM
5.3 Flash a useful high-volume challenger to DeepSeek V4.1 Flash; endpoint
latency, throughput and prices differ substantially by provider. Compare
completed synthetic tasks per minute and cost per successful task, not vendor
benchmarks or advertised tok/s alone. Recheck routes and billed provider when
credits are available. The endpoint catalog does not prove account/key ZDR
enforcement; verify that control in OpenRouter before sending competition data.

## Resume checklist

1. Read `AGENTS.md`, `README.md`, `docs/ad-playbook.md`, and
   `docs/model-selection.md`.
2. Before any model inference, inspect the key limit and ZDR controls. Keep all
   evaluation within the remaining $60 personal ceiling.
3. Re-run the local tests, `bin/ctf-codex doctor`, and the synthetic operations
   drill after changes.
4. When event material is published, initialize one workspace per service and
   fill its scope, checker, flag-ID, expiry and rollback facts from that source.
   Populate `scope/published-targets.txt` only with published authorized proxy
   URLs and keep captures under `evidence/raw/` with private permissions.
5. Verify the event submission API contract and test an adapter locally before
   configuring it. Preserve the flagkeeper's explicit user signal and held
   ledger; do not introduce phase or model eligibility gates.
6. Run the synthetic A/B tasks with credits under the evaluation cap, record
   actual billed route and task outcomes, then adjust per-role native model
   settings only if the measured results justify it.

The user-provided `exploit-web-template.py` and `tulip_replay.py` in Downloads
were reviewed as reference code and not executed. Their unmodified defaults
include broad guessed target ranges, a continuous threaded farm loop, direct
TCP submission, disabled TLS verification, and flag output. Use the bounded
adapter and reproduction instructions instead.
