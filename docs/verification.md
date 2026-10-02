# Verification - 2026-10-02

The current launcher uses Codex CLI 0.159.2 under Ubuntu/WSL with
`stealth/space-bunny-alpha` through OpenRouter. The Windows CLI on this host
rejected shell tools under its host policy; the WSL CLI completed a live
inference, shell read, file write and replay smoke. `./codex-ctf` installs an
isolated configuration, 12 native agents, A/D skills and custom prompts under
ignored `.runtime/codex/`. `doctor` validates all seven profiles without
inference. Native prompt discovery found `/prompts:brrrr` and
`/prompts:chillax`.

The full and `brrrr` loops used native Codex agents against the authorized
offline FAUST clone. They covered four service interfaces and demonstrated
synthetic IMC and LAMP attacks with patch, rollback and normal-flow replay.
ALF parser memory corruption was confirmed as a worker crash, without flag
access or RCE proof. The focused ALF and Rufflecopter closeout stopped on
OpenRouter's daily 429. Details and saved evidence are under ignored
`.runtime/coordination/` and `.runtime/codex/sessions/`.

The launcher retains sessions for agent-level token accounting from the
focused closeout onward. The first two loops used `--ephemeral`, so only root
usage is recoverable for them. A complete exact all-agent token total is
therefore unavailable. The daily free-model cap also prevented live
`chillax` exercise. No official checker, live flag placement, score,
submission or competition-network test was available on the offline image.

The saved focused team session stopped on HTTP 429. The launcher now supports
non-interactive `resume --exec --json SESSION_ID` dispatch so the closeout can
continue that session without creating a duplicate team run. Dispatch tests
cover the sandbox, provider binding, session selector, prompt and output path;
actual resume execution remains pending the provider reset.

Local checks: Python suite, shell syntax, strict config, native prompt
construction and diff whitespace checks passed on 2026-10-02. The Python suite
ran 71 tests with one optional `tshark` skip, including dispatch checks for
the single-agent `run`, `audit`, `traffic` and `patch` commands. After backing
up stale SQLite state from an earlier Codex build, the Ubuntu TUI opened and
displayed Space Bunny as its selected model. A passed local or synthetic check does not
establish an official checker result.
