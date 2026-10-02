# Local evidence and handoff

Keep source copies, captures, findings, and private handoffs under ignored
`.runtime/`. Record the deployed revision, exact evidence locations, current
hypothesis, next check, patch status, and rollback before a model change or
compaction. Never overwrite raw evidence or display flags, credentials, or keys.

Index traffic before reading bodies. `scripts/pcap-index.py` identifies times,
addresses, ports, and streams; inspect only selected streams and redact secrets
before sending excerpts to the model. State gaps and TLS visibility limits.
