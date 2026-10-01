# Service audit lenses

Use only lenses relevant to the deployed stack. Each lead needs attacker-controlled entry, a reachable path, a failed guard, and concrete flag or service impact. Track reviewed surfaces and unresolved leads.

## Architecture and ownership

- Enumerate handlers/middleware from the actual boot command. Compare protected/unprotected routes, alternate verbs, aliases, trailing slash, route precedence, upgrades, and internal-only assumptions exposed by the proxy.
- Follow public flag IDs through every read/write path: detail, list, search, export, attachment, and bulk. Verify ownership on the selected object with two synthetic users and distinct records.
- Inspect races and background jobs around tick-driven flag changes. Track persistence, initialization, and restart behavior. A patch that breaks checker is a failed patch.

## Parsing and transformation

- Compare proxy, router, and app interpretations of path, host, query, framing, and content type. Use local tests for request-smuggling or parser differentials that could disrupt a live service.
- Check percent encoding, Unicode, null bytes, separators, dot segments, symlinks, archive entry paths, and filename checks before versus after resolution.
- Check duplicate keys, array/scalar confusion, implicit booleans, prototype-sensitive keys, signed/unsigned conversions, integer overflow, boundary lengths, and partial reads. Change one property at a time in local validation.
- Trace deserialization, templates, command execution, database queries, and dynamic file reads from input through all guards to the sink.

## Native binary

- Establish architecture/ABI, linking, stripped status, runtime libraries, hardening, and actual executable hash. `file`, `readelf`, `objdump`, `nm`, `strings`, debugger, and decompiler output can guide review. Missing PIE/NX/RELRO/canary is context, not proof of a bug.
- Draw framing and state transitions. Track each length/value from receive to allocation, copy, parse, and output; inspect widths, signed conversions, arithmetic ordering, lifetime, and error cleanup.
- Prefer a local isolated reproducer with sanitizer or debugger evidence. Record exact bytes, trace/crash location, and whether the failure reaches flag data. Do not run crash-inducing tests against live scoring services or execute unknown binaries with host secrets and privileges.

## Configuration and dependency

- Inspect Dockerfile/Compose, effective env, mounts, secrets, capabilities, user, network exposure, filesystem permissions, and container-to-host interfaces. Focus on reachability through the designated service.
- Derive exact versions from lockfile and runtime, including transitive, vendored, statically linked, and image packages. For an advisory, check affected ranges, backports, triggering API, configuration, and path from attacker input. Cite an authoritative advisory or patch when available. Age or an SCA alert alone is insufficient.

## Regression matrix

| Case | Expected result |
| --- | --- |
| Checker-like create/read with synthetic flag | Same response and persistence as baseline |
| Authorized user reads own object | Success |
| Unauthorized user reads another object | Rejected without leakage |
| Original exploit input | Blocked without crash |
| Alternate encoding, order, or state | No bypass; normal input accepted |
| Restart and next checker/tick if observable | Service healthy; flags placed and retrieved |

Record actual inputs and results, not only `passed`. Revert if expected behavior regresses.
