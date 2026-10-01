# Shared workspace and cheap-model workflow

Read `service.toml` once, then update unknowns from runtime evidence. Work under:
`source/`, `evidence/raw/`, `evidence/derived/`, `findings/`, `patches/`, and
`verification/`. No remote target or checker response is assumed.

Use `findings/<service>-NNN.md` for both skills. Before compaction/profile changes,
write the deployed revision, exact evidence locations, current hypothesis, ruled-
out alternatives, next discriminating test, patch status and writer/rollback.
Never overwrite raw evidence. Keep one record per root cause.

Traffic starts with metadata and a checker baseline. The local
`pcap-index.py` tool emits frame times, addresses, ports and stream IDs, without
HTTP bodies, paths, headers or flags. It is an index, not full reconstruction.
Inspect selected streams locally, redact secrets, then feed bounded excerpts to
Codex. Record gaps, TLS visibility and proxy/NAT limitations.

Use the low-effort traffic/cheap profiles for indexing and summarizing. Use the
high-effort audit/patch profiles for causal reasoning and regression decisions.
Native Codex commands, apply_patch and tool-result replay do the work; no script
makes model decisions or delegates tasks. Escalate effort only after a concrete
lead. Ask Codex to write a handoff before `/compact` or `/model`.

Workflow contract: do not display real flags, keys or credential-bearing files.
This is not an automatic redaction guarantee. Review locally derived excerpts
before exposing them through model-visible tool output.
