Use $ad-ctf-team. This is the user's explicit request for parallel agent work:
start the five roles in team.toml with native Codex spawn tools. Workers
communicate through role inbox files and handoffs; the primary relays urgent
messages with native agent tools. Direct sibling messaging was unavailable in
a synthetic CLI test. Read $ad-ctf-team for the communication protocol.
Read team.toml and AGENTS.md; discover the actual services and available inputs.
Keep the primary thread as coordinator. Delegate independent bounded work,
scale when the backlog warrants it, and preserve one writer per service.
Start useful offline work even if no live services or endpoint credentials exist.
The flagkeeper holds flags until the user explicitly signals submission.
Warn about expiry without automatically flushing. Do not invent event API details.
