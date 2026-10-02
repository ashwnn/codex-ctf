# Harness design

`./codex-ctf` opens native Codex in the repository root. The launcher installs
an isolated configuration and the repository's agents, skills and prompts under
ignored `.runtime/codex/`. Codex owns inference, tool calls and native agent
coordination. The launcher creates no service workspaces or required manifests.

The default model is `stealth/space-bunny-alpha`; the default agents inherit it.
OpenRouter reads `OPENROUTER_API_KEY` from the launch environment. Shell tools
filter key, token and secret variables. Private event files stay under
`.runtime/` and never enter Git.

The team profile permits up to twenty native agents. AGENTS.md asks for five
bounded roles after the user's first context message. Native custom prompts
switch the session to points-first `/prompts:brrrr` or low-token
`/prompts:chillax` behavior. Agent count follows useful independent work;
there is no custom scheduler or routing layer.

The assigned VulnBox and documented service ports are the only default live
scope. Prompt scope is not a network firewall. A host allowlist is needed if
hard outbound containment is required. Flag submission needs a separate current
user instruction.
