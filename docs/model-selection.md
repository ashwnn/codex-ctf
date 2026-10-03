# Model selection

The default model is `deepseek/deepseek-v4.1-flash`. Every default agent
inherits it. `--profile mimo` selects `xiaomi/mimo-v2.6-flash`; any other model
can be selected explicitly with `--model VENDOR/MODEL`. There is no model
router or automatic model fallback.

`./codex-ctf models MODEL` reads current OpenRouter metadata. Treat prices,
availability and context size as time-sensitive; confirm actual usage from
OpenRouter and the CLI JSON events before comparing costs.

`./codex-ctf run` starts a single-agent interactive session with the `cheap`
profile. That profile uses low reasoning effort and limits tool output to 2,000
tokens. It uses the default model and does not add a workflow prompt; provide
the task in the first message. `./codex-ctf` starts the `team` profile for the
full CTF workflow.

In an active team session, `/prompts:chillax` asks the primary agent to keep
at most one useful worker and use bounded output. `/prompts:brrrr` permits more
parallel work when the backlog has distinct tasks. These prompts do not change
the model or launch profile. Neither mode automatically picks a cheaper model;
check model pricing separately before choosing `--profile mimo` or `--model`.
