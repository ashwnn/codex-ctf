# Model selection

The default model is `deepseek/deepseek-v4.1-flash`. Every default agent
inherits it. `--profile mimo` selects `xiaomi/mimo-v2.6-flash`; any other model
can be selected explicitly with `--model VENDOR/MODEL`. There is no model
router or automatic model fallback.

`./codex-ctf models MODEL` reads current OpenRouter metadata. Treat prices,
availability and context size as time-sensitive; confirm actual usage from
OpenRouter and the CLI JSON events before comparing costs.

`/prompts:chillax` reduces worker count and tool output. `/prompts:brrrr`
permits more parallel work when the backlog has distinct tasks. Those prompts
do not silently swap models.
