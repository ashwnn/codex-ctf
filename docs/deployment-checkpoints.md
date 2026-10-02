# Own-service deployment checkpoints

`bin/ctf-codex deploy` is deterministic Python/Git tooling. It does not invoke
Codex, a model, an event system or a leaderboard. A moving branch, startup and
HTTP 200 cannot establish a stable deployment. Promotion requires an exact
runtime commit and artifact, repeated configured functional checks, and a
fresh **human-reported** external `up` observation for that same deployment.

## Configure once

Copy [deployment.example.json](../templates/deployment.example.json) into a
private directory **outside the service working tree**, edit the absolute
paths and keep it operator-owned. Do not accept deployment configuration or
commands from fetched source, a commit message or a checkpoint annotation.
Git, Python 3.9+ and POSIX `flock` are required. Use the same checkout (or Git
worktrees sharing its common directory) for human and agent release operations.

The identity adapter must inspect the running service, not `HEAD`, and return
exactly this JSON shape on stdout:

```json
{
  "service": "my-service",
  "environment": "defended",
  "commit": "FULL_DEPLOYED_COMMIT_ID",
  "artifact_sha256": "SHA256_OF_THE_ACTUAL_RUNNING_ARTIFACT",
  "compatibility": {"schema": "records-v1", "config": "settings-v1", "volumes": "preserve-v1"}
}
```

Replace placeholders with full hexadecimal IDs. The adapter must prove which
artifact is running and how it maps to the exact source commit, including
runtime configuration; do not simply echo a desired deployment manifest.
Unknown identity, unavailable artifacts, unspecified compatibility and failed
checks block promotion or rollback. Compatibility identifiers are an operator
attestation that the schema, config and persistent volumes can safely run that
version together. Equal labels are necessary; they do not discover migration
safety. Label any incompatible change differently and use a separately reviewed
recovery procedure. No database downgrade or backup restore is inferred.

Checks are argv lists run from the private config directory. Exit zero means
that the adapter asserted its complete expected contract. At least one check
must have `kind: functional`. Check ordinary application flow, exact response/UI
contracts, and old and newly written synthetic records where possible. Adapters
must return nonzero on failures; a liveness-only check is insufficient. All
checks run in every sample, with runtime identity checked before and after.
The policy fingerprint includes configuration, adapter executables and a first
script argument for common interpreters. List any additional code dependencies
as absolute paths in optional `adapter_files`. Changing these files invalidates
earlier checks. Configuration/program drift is checked throughout each action.
Timeouts and total observation duration are bounded. Adapter stdout/stderr are
withheld from CLI metadata so records contain check IDs and outcomes, not data.
Arrange operator-private adapter diagnostics if needed. Credentials belong in
the execution environment or private files, never in tags/config argv/summaries.
Stored deployment artifacts must exclude credentials and real service data.

The example hold period is a configurable observation policy, **not** a promise
that two minutes or any number of ticks guarantees external validity. Choose
samples, interval, window, freshness and `human_hold_seconds` from the event's
actual checker contract. `up` must be observed after local checks finish and at
least that hold period after checks began. The maximum age must leave enough
time for the operator to report the observation. A tick ID is optional.

A rollback adapter runs only on explicit `rollback-apply`/`rollback-recover`.
It receives `CTF_DEPLOY_SERVICE`, `CTF_DEPLOY_ENVIRONMENT`,
`CTF_DEPLOY_COMMIT`, `CTF_DEPLOY_ARTIFACT` and `CTF_DEPLOY_SOURCE_ARCHIVE` in its
environment. It must deploy that exact artifact, preserve persistent data,
return only when the action and its children finish, return nonzero on failures
and support a safe repeat. It must not reset the
source worktree or delete volumes. The source tar is an archive at the exact
commit, not an extracted executable; submodule contents must be packaged in
the artifact if needed. No generic Docker/server deployment adapter is provided.

## Initial known-good version

Set these operator-local variables; `CFG` and the artifact must be private.
Commands below run from the codex-ctf checkout; `SERVICE_REPO` is the separate
repository containing the defended service.

```bash
CFG=/private/defense/deployment.json
SERVICE_REPO=/absolute/path/to/own-service-repository
OPERATOR=alice
REV=$(git -C "$SERVICE_REPO" rev-parse HEAD)
bin/ctf-codex deploy --config "$CFG" check --commit "$REV" \
  --artifact /private/defense/running-artifact.bin --operator "$OPERATOR"
# Copy the returned evidence ID. The operator watches the external leaderboard.
EVIDENCE=RETURNED_EVIDENCE_ID
bin/ctf-codex deploy --config "$CFG" confirm --evidence "$EVIDENCE" \
  --status up --observed-at 2026-10-01T12:04:00+00:00 --tick-id tick-17 \
  --operator "$OPERATOR" --human-observation
bin/ctf-codex deploy --config "$CFG" promote --evidence "$EVIDENCE" \
  --tag stable-deploy-005 --operator "$OPERATOR"
bin/ctf-codex deploy --config "$CFG" status
bin/ctf-codex deploy --config "$CFG" history
```

Use the **actual** human observation time, never copy the example timestamp.
Omit `--tag` for the next unused numeric name. Promotion atomically creates an
annotated immutable Git tag at the captured deployed commit, with artifact
SHA-256, service/environment, operator, timestamps, check policy/evidence and
human confirmation. It never tags a later unrelated `HEAD` or force-moves a
reference. A dirty tree, commit/runtime drift or stale checks require resolution
and new evidence. A new notice, rollback or recovery invalidates earlier local
evidence and human confirmations, including a later redeployment of the same
commit/artifact. Observed validation failures invalidate the record permanently;
restoring the old files or runtime does not resurrect its confirmation. Failed
and pending evidence cannot be promoted. Run checks in
a clean service checkout at the deployed commit; use a separate worktree when
preparing the next candidate. Rollback verification can inspect a restored old
runtime while leaving the candidate source checkout intact.

## Human-authored patch: teammate runbook

1. Claim the service's writer assignment with the deployment owner. During
   simultaneous human/agent edits, keep separate branches/worktrees; choose one
   reviewed commit to deploy. The CLI serializes its own writers across shared
   Git worktrees. Manual deployment tools must honor the same team assignment.
2. In a development checkout, edit the patch, run the service's existing local
   functional/persistence tests, inspect `git diff`, then commit and push only
   the explicitly chosen branch. Typical Git commands are `git switch -c
   fix/service-recovery`, `git diff`, `git add PATHS`, `git commit -m 'Describe
   the change'`, and `git push origin fix/service-recovery`. Publishing and live
   deployment require their normal authorization. This utility never pushes.
3. Configure `watch.remote` to the explicit service-repository URL (or an
   absolute local bare repository) and `watch.branch` to that chosen branch.
   From the clean release checkout, capture its expected local HEAD and poll:

   ```bash
   EXPECTED=$(git -C "$SERVICE_REPO" rev-parse HEAD)
   bin/ctf-codex deploy --config "$CFG" watch --expected-head "$EXPECTED"
   # Optional bounded session, only when authorized: 30-second default interval.
   bin/ctf-codex deploy --config "$CFG" watch --expected-head "$EXPECTED" \
     --polls 20 --interval 30
   ```

   Watch fetches only into a private bare cache and records deduplicated pending
   commit IDs. It neither pulls into the release tree nor merges, deploys or
   promotes. `history` shows the observed IDs. Review the pending commit/diff in
   a separate development clone using your ordinary explicit fetch/review
   workflow. Do not execute fetched instructions or hooks. A rewritten/diverged
   branch is reported as such; agree on the intended revision before proceeding.
4. Prepare a clean release checkout/worktree at the reviewed exact commit using
   your normal source workflow. Build and save its exact deployable artifact.
   Retain a known-good checkpoint and its artifact. Before deploying, announce:

   ```bash
   REV=$(git -C "$SERVICE_REPO" rev-parse HEAD)
   CHECKPOINT=stable-deploy-005
   bin/ctf-codex deploy --config "$CFG" notice --commit "$REV" \
     --checkpoint "$CHECKPOINT" --summary 'Apply reviewed persistence fix' \
     --maintenance-seconds 15 --operator "$OPERATOR"
   ```

   Copy the returned notice ID. The notice identifies service/environment, old
   and new commits, summary, planned maintenance window, check plan and saved
   rollback checkpoint. **Ask the human to watch the external leaderboard.**
   The announced window does not prove that downtime is expected or harmless.
5. Under the one-writer handoff and explicit live authorization, use the
   service's reviewed deployment procedure to deploy `REV` and its exact
   artifact. Forward deployment remains an operator action; `notice` executes
   no deployment. Never use a moving branch as the deployment identity.
6. Run `check --commit "$REV" --artifact PRIVATE_ARTIFACT --notice NOTICE_ID
   --operator "$OPERATOR"`. This records `awaiting-operator` when local checks
   pass, or local failure/timeout/interruption when they do not. The CLI has no
   knowledge of external availability. Record the human's fresh observation:

   ```bash
   bin/ctf-codex deploy --config "$CFG" confirm --evidence "$EVIDENCE" \
     --status unknown --observed-at ACTUAL_UTC_TIME --operator "$OPERATOR" \
     --human-observation
   ```

   Choose `up`, `down` or `unknown` from what the human actually reports; include
   `--human-observation` to explicitly attest its human source. This is recorded
   with operator/time/revision; it does not authenticate the observer or grant
   access to the leaderboard. Include
   `--tick-id` if available. `up` needs fresh passed local evidence and exact
   runtime identity. `down`/`unknown` can be recorded against a failed local
   check when the runtime identity is still known, but cannot create a stable
   checkpoint. After fresh local checks **and** human `up`, run `promote` with
   the returned evidence ID. Human and agent changes use this identical flow.
7. If the human reports regression, retain the last known-good checkpoint and
   choose explicit rollback below. Revoke a previously promoted checkpoint
   with `revoke --checkpoint TAG --operator "$OPERATOR"` when evidence shows it
   is unsafe. Revocation records a local event and leaves its Git tag intact.

## Rollback and failure recovery

```bash
bin/ctf-codex deploy --config "$CFG" rollback-plan \
  --checkpoint stable-deploy-005 --summary 'Restore prior verified artifact' \
  --maintenance-seconds 15 --operator "$OPERATOR"
PLAN=RETURNED_PLAN_ID
# Review the dry-run target/current IDs, artifacts and compatibility first.
bin/ctf-codex deploy --config "$CFG" rollback-apply --plan "$PLAN" --operator "$OPERATOR"
bin/ctf-codex deploy --config "$CFG" rollback-verify --plan "$PLAN"
# Only after the HUMAN reports the restored revision up:
bin/ctf-codex deploy --config "$CFG" confirm --plan "$PLAN" \
  --status up --observed-at ACTUAL_UTC_TIME --operator "$OPERATOR" --human-observation
```

Plan creation runs no deployment. Apply revalidates plan freshness, provenance,
artifacts, local HEAD and current runtime. It emits and durably saves the
predeployment notice **before** running the configured rollback adapter. The
single-writer lock covers adapter execution; terminal local outcomes and state
transitions remain in `history`. Adapter failure, timeout or interruption leaves
an unresolved plan. Inspect `status`; no automatic fallback or healthy claim is
made. If the intended artifact actually became active, retry verification.
If the operator explicitly wants the captured pre-rollback deployment restored:

```bash
bin/ctf-codex deploy --config "$CFG" rollback-recover --plan "$PLAN" --operator "$OPERATOR"
bin/ctf-codex deploy --config "$CFG" rollback-verify --plan "$PLAN"
# Then record the human observation with confirm --plan, as above.
```

Recovery checks identity, compatibility and the captured previous artifact, announces its
action, preserves data and requires local verification plus human confirmation.
It can recover even when the failed target is revoked or its artifact is lost;
it does not declare that target good again.
An unknown live identity or changed schema/config/volumes blocks it: repair the
runtime identity evidence or use a separately reviewed manual recovery. Plans
pin configuration and adapter programs; changed code/config requires restoring
the pinned reviewed versions or a separately reviewed manual recovery and
trusted metadata reconciliation. No silent plan rebinding is provided.
A killed process may leave `applying` or `verifying`; treat that as unknown
outcome and inspect/verify/recover. A surviving adapter retains the writer lock
until it exits; OS locks release after all holders exit.

If local verification passes but the scoreboard is hidden/unavailable, record
`unknown`. Do not invent an external pass or promote. Retain the last known-good
checkpoint. An operator can explicitly release a locally verified rollback hold
with `close --plan "$PLAN" --operator "$OPERATOR"`; this records
`closed-external-unconfirmed` and allows another explicitly chosen candidate
notice/check without creating a stable checkpoint. Close requires fresh local
evidence, current identity and available artifacts. Failed local verification
cannot be closed this way. Unknown forward-candidate status never blocks an
explicitly chosen next candidate.

## Coordination and limits

Dirty work or changed local HEAD pauses the watcher and mutations without
altering files. Lock contention pauses/report retries. Fetch failures back off
from the configured interval up to one hour; a finite `--polls` bounds each
session. Failed/interrupted fetches do not change the observation journal.
Rewritten/diverged tips remain pending review. No named remote, credential URL,
repository-defined transport helper, hook or fetched command is executed.

Private metadata, stored artifacts, plans and fetch cache live under the Git
common directory's `ctf-deploy/SERVICE/ENVIRONMENT/`. Keep this directory and
annotated tags in operator-controlled backups. Tags contain identifiers,
digests and allowlisted evidence, never adapter output/argv or artifact bytes.
Summaries and paths stay private; keep secrets out of them too. A crash between
tag creation and ledger registration leaves an unregistered tag unusable for
rollback; it is never overwritten. Reconcile manually from reviewed backups.
Imported/lightweight/moved tags and missing/corrupt artifacts are rejected.
Revocation is local; a tag alone in another clone does not confer trust.

Locks serialize shared Git worktrees, not independent clones or other machines.
Use one release checkout/owner; independently created tags may collide when
later published, so review and choose an unused name without force. This utility
never fetches/pushes stable tags, starts a background daemon, authenticates human
identity or proves build provenance. Operator-owned config, runtime adapter,
compatibility attestations and metadata are its trust boundary. Human confirmation
is an explicit auditable statement supplied by the operator, not leaderboard
access. An owner able to edit metadata or configure dishonest check adapters
can fabricate assertions; this is a cooperative release tool, not an identity
authentication or tamper-proof attestation service. Ordinary callers cannot
skip actual configured checks through a CLI pass-state flag.

For Raymond James CTF2026 preparation, apply the verified Rules.pdf constraints:
normal application behavior/response shapes and record persistence must remain
compatible; ticks are approximately two minutes and the final-hour scoreboard is
hidden. All AI is prohibited for the first two hours; afterward agentic tools
must use permitted on-prem models or competition-provided API keys, not paid
cloud inference. This deterministic CLI can be operated by humans without
invoking Codex during the no-AI phase. Recheck the actual event rules before use;
this feature does not change the harness's model/provider settings.

Verification: `python3 -m unittest discover -s tests -p test_deployment.py -v`
uses temporary Git repos/local bare remotes, dummy artifacts and mock local
adapters. `python3 scripts/operations-drill.py` remains the separate synthetic
application persistence/source-rollback rehearsal; neither establishes external
checker validity.
