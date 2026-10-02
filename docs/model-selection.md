# Model selection

The default model is `stealth/space-bunny-alpha` for the current offline harness
test. Every default agent inherits that model. Select another complete
OpenRouter slug explicitly with `--model VENDOR/MODEL` or a named profile.
There is no model router or automatic provider fallback.

`./codex-ctf models` reads current OpenRouter metadata. Treat preview price,
availability and context size as time-sensitive. The Codex CLI may lack local
metadata for this preview and use fallback metadata; confirm actual usage from
OpenRouter and the CLI JSON events before comparing costs.

`/prompts:chillax` reduces worker count and tool output. `/prompts:brrrr`
permits more parallel work when the backlog has distinct tasks. Those prompts
do not silently swap models.
