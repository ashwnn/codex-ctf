# Model selection

The default model is `qwen/qwen3.8-27b:free`. Every default agent inherits it.
The loopback relay tries all currently free, ZDR-listed tool models, then paid
`deepseek/deepseek-v4.1-flash` and `xiaomi/mimo-v2.6-flash`, in that order,
when a model returns 429, 502, 503 or 504 before streaming. It adds
`provider.zdr=true` to every Responses request. An error after streaming begins
ends that request without replay. `--profile mimo` or `--model VENDOR/MODEL`
pins a single model, with ZDR still enforced.

`./codex-ctf models --free-zdr` reads OpenRouter's current model and ZDR
endpoint catalogs without using a key or making an inference request. It lists
zero-priced, tool-capable ZDR endpoints. The relay checks this catalog at first
use and fails closed if it cannot be read. It does not route to a free model if
any of its available ZDR endpoints has a price or lacks tools. OpenRouter's
free request allowance is shared by the account; rotating models does not
multiply it. The paid fallbacks require account credits, and actual inference
through the relay must be checked with a configured API key.

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
