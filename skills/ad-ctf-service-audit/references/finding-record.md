# Shared A/D finding record

Use one record per root cause as the handoff between `$ad-ctf-traffic-reconstruction` and `$ad-ctf-service-audit`. A concrete location means file:line, binary function/offset, config key, PCAP filename/frame/UTC time, or log request ID. Redact real flags, tokens, keys, and credentials.

```yaml
id: "stable local finding ID"
service: "name and designated interface"
status: "hypothesis | observed | correlated | reproduced locally | confirmed"
priority: "severity, flag impact, active exploitation, and uptime risk"
scope_and_rules: "published event scope and current active-test bounds"
environment: "deployed revision/image/hash, topology, clock offset"
evidence:
  - "precise location, raw versus decoded detail, observed result"
alternatives: ["checker retry, unrelated crash, or other explanation"]
entry_point: "method/route or protocol message"
controlled_input: "fields, encoding, and constraints"
trust_boundary: "intended invariant and where it fails"
causal_chain: "input -> transformations -> sink/state -> effect"
impact: "concrete flag or service effect"
reproduction: "isolated synthetic-data steps and actual/expected results"
patch: "minimal applied change or proposed change, plus rollback"
verification: "baseline, negative, alternate, flag lifecycle, checker/tick outcome"
confidence_and_gaps: "observation versus inference and missing evidence"
```

Do not label an attack confirmed without a demonstrated root cause and impact. An observed pattern alone is not a reproduced bug. Record a proposed patch as proposed and report any checker regression explicitly.
