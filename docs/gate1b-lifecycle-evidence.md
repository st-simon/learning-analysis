# Gate 1B lifecycle evidence

Date: 2026-09-18
Proposal: `20260918-wechat-reader-gate1b-lifecycle`
Status: B0-B5 passed; Gate 1B verified and disposable runtime removed.

This record contains no API key, article URL, article body, browser token, or raw environment. Gate 1B uses zero article calls.

## P7B

B0 deterministic and static evidence:

- A generated plist contains only the fixed label, Python lifecycle entry point, project working directory, `RunAtLoad`, `KeepAlive`, `ThrottleInterval=10`, `ProcessType=Background`, and local log paths.
- The plist contains no `EnvironmentVariables`, control-plane key name, token, or secret value.
- The runtime reads only `CONTROL_PLANE_API_KEY` from a regular `.env` file whose group/world permission bits are zero; it parses data without shell evaluation and rejects missing, duplicate, empty, or insecure key files.
- The tunnel command contains fixed binary/config/PID/health/log arguments and no secret.
- Installation prepares only the fixed plist, Gate 1B runtime directory, and two Gate 1B logs with `0600/0700` permissions; it refuses to overwrite an existing agent.
- Cleanup unlinks only the fixed plist and named Gate 1B files, refuses non-empty owned directories, and preserves unrelated runtime files and other LaunchAgents.
- A kill target is accepted only when the PID file, launchctl PID, and expected tunnel-client executable all match.

Verification:

- Red signals were observed before each interface existed: plist module import, secret parser/command builder, and install/cleanup/kill validation.
- Green: 10 Gate 1B unit tests passed.
- Full Python suite: 44 tests passed, 1 opt-in socket test skipped in the sandbox.
- Node capture flow: 6 tests passed.
- MCP smoke passed.
- Generated plist passed `plutil -lint` and the secret-name scan returned no match.
- Proposal readiness and `git diff --check` passed.

Decision: `passed` for B0/P7B static and deterministic scope. Native user-domain installation was subsequently exercised in P7A and removed in P17.

## P7A

Observed on macOS 15 in the current user's `gui/501` domain:

- `launchctl bootstrap` installed the disposable agent without `root` or `sudo`.
- The service entered `running` with PID `24681`; `last exit code = (never exited)`.
- The PID and health-URL files were created with mode `0600`; both Gate 1B logs were mode `0600`, and stderr was empty.
- The first lifecycle status call occurred before readiness and returned the generic operation-failed envelope. No reinstall or blind retry was performed.
- Targeted evidence then showed the agent running. The official tunnel health command reported the same PID, `healthz=live`, `readyz=ready`, and a successful control-plane poll.
- The second lifecycle status check returned `status=ok`, `ready=true`, PID `24681`.

Decision: `passed` for B1/P7A. The observed startup has a short readiness window; this spike does not yet claim instant readiness or natural login-start behavior.

## P9A

Observed after the single permitted controlled termination:

- The validated old launchd/PID-file process, PID `24681`, was terminated exactly once.
- launchd reported `runs=2`, generated new PID `25377`, and recorded the previous exit code as `0`.
- The new tunnel instance ID is `8f3ed922913d2254a2543075a0b866a2`, distinct from the baseline instance.
- The first lifecycle status call again landed inside the short readiness window. No second termination, reinstall, or restart was attempted.
- The official health command then reported PID `25377`, `healthz=live`, `readyz=ready`, and a successful control-plane poll on a new loopback health endpoint.
- The second lifecycle status check returned `status=ok`, `ready=true`, PID `25377`.

Decision: `passed` for B3/P9A. One controlled kill recovered to a new, healthy instance within the 45-second bound and without a duplicate process.

## P9B

Baseline B2 passed:

- The ChatGPT desktop App returned the exact fixed `gate0-transport-v1` fixture with `status=ok`, `network_used=false`, and `persistent_write=false`.
- At the same time, the Gate 1B tunnel log recorded two dispatcher-to-MCP events under client instance `eae2e4bfb5f46324fb8ecc8b6e4f8d71`, the instance whose PID file and launchd service both identified PID `24681`.
- No article URL, article body, browser extension, capture bridge, Jina, or Cloudflare path was used.

Recovery B4 also passed:

- The ChatGPT desktop App returned the same fixed fixture after recovery.
- The corresponding dispatcher events were logged under recovered client instance `8f3ed922913d2254a2543075a0b866a2`, whose launchd and PID-file identity was PID `25377`.

Decision: `passed` for B2+B4/P9B. Both fixed App probes were forwarded by the expected pre- and post-recovery instances.

## P17

Mandatory B5 cleanup passed:

- Before cleanup, a value-only scan confirmed that neither the control-plane secret value nor a WeChat article URL appeared in the generated plist or Gate 1B logs.
- `bootout` and exact-owned-file cleanup returned `removed=true`.
- The fixed launchd label, plist, `runtime/gate1b`, and `logs/gate1b` were absent afterward.
- No Gate 1B process remained, and neither prior test health port (`58303`, `58446`) had a listener.
- Git retained only reviewable source, tests, proposal, evidence, and documentation changes; runtime artifacts were not added.

Decision: `passed` for B5/P17. The disposable runtime was fully removed without touching unrelated services or files.

## Final decision

Gate 1B is `verified`: B0-B5 passed with zero article calls, one controlled termination, two fixed App probes, USD 0 cost, and complete cleanup. This proves disposable user-domain supervision and one recovery cycle for the tunnel/MCP control path. It does not prove natural login/restart startup, capture-bridge persistence, Web behavior, Windows behavior, or a production installation experience; those remain for a separately approved full-implementation proposal.
