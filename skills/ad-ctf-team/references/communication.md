# Native Codex team communication

Codex CLI 0.159.2 with the selected OpenRouter model was tested on October 1,
2026. The primary spawned, messaged and waited for a child. In a separate
two-child test, the children did not have `send_input` or another sibling
messaging tool. They could not directly send PING/PONG. Use the shared
workspace and primary relay for peer communication; do not claim direct native
sibling messaging is available until a future client/model test proves it.

The coordinator writes `.runtime/coordination/roster.md` with role, native ID, assignment
and handoff path. Each worker owns `.runtime/coordination/<role>.md`. For a peer-directed
message, create a small file under `.runtime/coordination/inbox/<recipient-role>/` named
`<UTC-basic-time>-<sender-role>-<finding-id>.md`. Use a unique suffix if needed.
Include recipient, sender, service, finding ID, UTC time, urgency, evidence path,
observation, confidence, requested action and response path. Never include raw
flags, credentials, traffic bodies or private source. Write a temporary file
then rename it into the inbox so readers see a complete message.

Read your inbox and relevant peer handoffs at assignment start, before acting
on a finding that a peer may have changed, and before finishing your task. Do
not busy-poll. After reading a message, record it in your handoff or reply via
the sender's inbox. For urgent findings, finish your bounded turn promptly and
state the recipient and message path in the final result; the primary can then
relay through native `send_input`/resume. The primary checks inboxes whenever a
worker returns or new evidence arrives, and delivers urgent messages to active
workers with native tools. Files are a shared Codex workspace artifact, not
an external daemon, router or agent loop.

The sole flagkeeper owns `.runtime/flags/ledger.sqlite3`. Attack agents may write only
unique JSONL files under `.runtime/flags/inbox/`, by atomically renaming completed
files into that directory. The launcher-managed submitter imports and submits them
when configured; the coordinator must not forward raw flag values. Keep one
code/deployment writer per service, and use the board to prevent duplicate
service/team attack shards.
