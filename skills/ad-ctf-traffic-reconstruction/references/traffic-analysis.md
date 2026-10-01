# Traffic analysis field guide

Use this reference for PCAPs or high-volume logs. Work from copies, preserve raw bytes, and filter to the published service port and time. A central proxy can collapse many opponents into one apparent source address.

## Fast pass

1. Check file type, capture timestamps, snaplen, link type, missing packets, protocol-dissection assumptions, and whether TLS or a proxy hides application payloads.
2. Count flows and request patterns by tick-sized time bucket. Cluster paths, methods, status, lengths, and client fingerprints. Compare a quiet baseline to suspicious intervals.
3. Select streams, reassemble and export raw requests/responses with headers and binary bodies. Save packet indices and times. Inspect sequence gaps and retransmissions before declaring a malformed request.
4. Correlate with proxy/app logs, container process and socket events, and storage changes. Apply explicit clock offset and note which identity headers can be forged.
5. Check whether a response exposed a dummy flag, read a different user's object, changed state, initiated egress, restarted the process, or only returned an error.

## Local tool examples

Adapt the display filter to the designated service. `http.*` fields may be empty for undecoded ports, other protocols, or encrypted bodies. A capture filter uses different syntax from a display filter.

```bash
capinfos service.pcap
tshark -r service.pcap -q -z conv,tcp
tshark -r service.pcap -Y 'tcp.port == 8080' -T fields -e frame.number -e frame.time_epoch -e ip.src -e ipv6.src -e tcp.stream -e http.request.method -e http.request.uri -e http.response.code
tshark -r service.pcap -q -z follow,tcp,raw,0
```

If Zeek is already installed, use its `conn.log` to index flows and its `uid` to join protocol logs. Treat tool output as evidence, not proof of exploitability. For large captures, isolate bounded intervals before export. For pcapng, inspect interface names and directions. A TCP stream number is local to one capture, not a stable cross-file identifier.

## Interpretation traps

- One TCP connection can carry multiple requests; one request can span packets. UDP requires its own transaction logic.
- Proxy and application may decode or canonicalize differently. Preserve raw path/body and every derived value; do not replace one with the other.
- Retransmission, fragmentation, truncation, packet loss, compression, and keep-alive can create duplicate or partial apparent messages.
- TLS without keys gives metadata, not HTTP bodies. Use logs where available and record the visibility limit.
- An apparent exfiltration destination may be expected DNS, telemetry, or package updates. Correlate timing and service code.
- A flag-shaped value in the team's own traffic may be a checker write/read. Redact it while investigating.

## Discriminating tests

Change one property at a time on an isolated instance. For access control, compare an authorized read of one's own synthetic object with an unauthorized read of a different synthetic object. For parser differences, record raw encoding, normalized path, handler, and selected object. For stateful bugs, retain request order and timing. If reproduction is impossible, identify missing evidence and leave the lead unconfirmed.
