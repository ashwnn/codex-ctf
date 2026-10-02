# A/D operating loop

Start with `./codex-ctf` and tell the TUI what you know about the assigned
VulnBox, connection and event. The harness starts five bounded native workers
when there is useful work. It stores private evidence under `.runtime/`.

1. Inventory the deployed services, exact documented interfaces and checker-like
   create/retrieve flows. Derive the own-box target from user or organizer evidence.
2. Compare source, deployed revision, Docker state and bounded traffic/logs.
3. Reproduce a supported finding on an isolated copy with synthetic data.
4. Make the smallest fix with one writer per service and a rollback path.
5. Verify normal flows, the original exploit, restart persistence and observed
   service health. Record what could not be checked.

Only the assigned VulnBox is a live target. Do not enumerate ports, contact
other teams or event infrastructure, or submit flags. The flagkeeper keeps
captured values private and reports counts.

`/prompts:brrrr` uses more agents for distinct points-producing work.
`/prompts:chillax` keeps the primary and at most one useful worker to save
tokens. The user can switch modes within the same session. Codex CLI uses the
`/prompts:name` syntax for custom prompts.
