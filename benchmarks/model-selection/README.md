# Model selection benchmark — synthetic fixtures

Use these fixtures for a small, repeatable OpenRouter/Codex model comparison.
They contain no real challenge source, flags, traffic or credentials. Keep run
logs and modified fixture copies under `.runtime/`; never commit them.

## Tasks

- **Audit:** inspect `audit/` and report the authorization flaw, exact source
  lines, expected unauthorized behavior and one safe regression case.
- **Traffic:** inspect `traffic/` and return the suspected unauthorized read,
  exact UTC lines, baseline comparison, confidence, and separate observations
  from inference.
- **Patch:** copy `patch/` to an isolated workspace, preserve the response
  contract, add owner/unauthorized/missing-record tests and run the full test.

The patch task has these objective checks: owner read remains `(200, {id, body})`;
unauthorized and missing records return the identical `(404, {error: not found})`;
tests pass; no network or unrelated files are used.

## Running a paired comparison

Use the same Codex CLI version, effort, prompt and clean fixture copy for every
candidate. Keep the model IDs fixed during a round and alternate run order on a
repeat. For each model/task pair, copy the fixture to a unique directory under
`.runtime/model-eval/`, then invoke the native Codex harness:

```bash
bin/ctf-codex run --workspace "$PWD/.runtime/model-eval/<model>/<task>" \
  --model VENDOR/MODEL --effort low --exec --json \
  --output "$PWD/.runtime/model-eval/<model>/<task>/final.txt" \
  'Read the task contract and assigned files. Complete only the requested task. Use local files and tools only; do not access the network or inspect outside this workspace.'
```

The existing `smoke` command always uses the configured model; it is not a model
override test. Do not use `Space Bunny Alpha` as the competition baseline: its
temporary free preview is not a ZDR-eligible endpoint. Set OpenRouter account/key
ZDR enforcement first, and check candidate endpoints with `bin/ctf-codex models
--zdr MODEL...`. That catalog read does not prove the account policy is active.

Score objective checks from the resulting files and command exit status. Record
end-to-end elapsed time, tool calls, retries/corrections, OpenRouter billed cost,
and correctness. Compare successful tasks per minute and cost per successful
task; advertised token/s alone omits first-token delay, reasoning, replayed
history and tool work. Human-score evidence quality and unsupported claims. Do
not create an automatic reviewer or model-selection service.

## Current run record

| Date | Candidate | Result | Cost |
| --- | --- | --- | --- |
| 2026-10-01 | DeepSeek V4.1 Flash | Not run: OpenRouter returned 402, account has never purchased credits. | $0 |
| 2026-10-01 | Qwen 3.8 27B Free | Not run: OpenRouter returned 429 before inference. | $0 |

No model won this round. Repeat the tasks after credits are available; keep the
pre-event evaluation spend at or below $5 of the personal $60 total budget.
