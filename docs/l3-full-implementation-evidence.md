# L3 full implementation evidence

Updated: 2026-09-20. Proposal: `20260918-wechat-reader-l3-full-implementation`.

This file records stage-gated implementation evidence. It contains no article
body, full article URL, token, cookie, environment value, or control-plane key.

## F0 — baseline freeze: passed

- Last known stable Git commit at entry: `40e7f34`.
- Existing Python baseline passed (44 tests, one opt-in loopback test skipped).
- Existing extension flow passed (6 Node tests).
- MCP stdio handshake, read-only tool discovery, fixed no-network probe, and
  unsafe URL rejection passed.
- Formal and disposable LaunchAgent labels and capture port had no residue.

## F1 — in-process capture runtime: passed

- `CaptureRuntime` owns one in-memory coordinator and one loopback adapter.
- `read_rendered_url` registers and waits on that coordinator directly; the old
  MCP-to-loopback `GET /capture` self-call and client were removed.
- The loopback surface is extension-only: `GET /pending`, `POST /capture`, and
  liveness-only `GET /healthz` on `127.0.0.1`.
- Concurrent URL isolation, exact extension identity, token checks, timeout,
  cancellation, cancel-all shutdown, and port close behavior passed.
- Two real loopback integration tests passed: exact paired submission and
  shutdown cancellation. No article or external network was used.

## F2 — formal lifecycle and installer: passed

- Formal label: `com.junxia.learning-analysis`.
- One user LaunchAgent starts one tunnel-client, which supervises the stdio MCP;
  the MCP owns the loopback capture runtime. No second bridge process exists.
- The installer emits a private extension copy and random per-install token
  under `runtime/learning-analysis`; directories are `0700`, sensitive files
  and logs are `0600`.
- `status --wait`, `doctor`, `upgrade`, and `uninstall` use exact owned paths and
  distinguish absent, starting, MCP, control-plane, capture, and configuration
  failures. Each health subprocess has its own timeout inside the 45-second
  outer bound.
- System plist lint passed. Formal install and doctor passed without root.
- Runtime inspection found one tunnel-client and one Python listener on
  `127.0.0.1:18431`; no separate capture bridge process was present.
- Logs contained no WeChat article URL, secret variable name, generated config
  variable name, or capture-token value.
- Current automated regression: 50 Python tests passed with three opt-in tests
  skipped in the sandbox; 6 Node tests passed. The two F1 loopback tests passed
  separately on the host.

## F3 — disposable end-to-end: passed

- The user loaded the generated private unpacked extension in Chrome and
  confirmed version `1.0.0` and fixed ID
  `bpannmkojgebmphkkngpnhkfcgfpnbhn`.
- A post-load formal doctor check passed for the agent, capture token, extension
  assets, control-plane path, and capture runtime.
- The ChatGPT desktop App fixed probe returned `status=ok`,
  `probe_id=gate0-transport-v1`, `fixture=local-mcp-no-network`,
  `network_used=false`, and `persistent_write=false` through the formal service.
- The ChatGPT Web fixed probe returned the same expected safe fixture through
  the formal service. App and Web transport preconditions therefore pass.
- In the ChatGPT desktop App, article 1 completed in the same tool call after
  one extension click. The extension ended at green `OK`; the tool returned
  `status=ok`, title `市场洞察SKILL：30分钟做出老板愿意看的市场分析`,
  `characters=4052`, `source_channel=rendered_dom`, `network_used=false`, and
  `persistent_write=false`.
- Post-call doctor passed. Exactly one tunnel-client and one MCP-owned listener
  on `127.0.0.1:18431` remained. Log scans found no article URL/slug, title,
  token value, or WeChat article URL pattern.
- Real-article allowance consumed: 1 of 2. The remaining article is reserved
  for F4 Web validation after natural login/restart.

## F4 — natural login: passed

- The user explicitly approved one macOS logout/login validation.
- Pre-logout baseline at `2026-09-20T02:43:18+0900`: formal doctor returned
  ready for PID `42075`; agent, capture token, and extension checks were all ok.
- After the user logged out and back in without running a terminal command,
  launchd created PID `47437` (process start `02:45:33`). Startup logs show the
  stdio MCP, health listener, and control-plane poller active by `02:45:45.472`,
  and tunnel metadata/start completed at `02:45:46.428`: about 13.4 seconds
  after process start and within the 45-second bound.
- A read-only post-login check found exactly one tunnel-client and one
  MCP-owned listener on `127.0.0.1:18431`; formal doctor returned ready with all
  local checks ok. No start, repair, or terminal action preceded recovery.
- The post-login ChatGPT App fixed probe returned `status=ok`,
  `probe_id=gate0-transport-v1`, `fixture=local-mcp-no-network`,
  `network_used=false`, and `persistent_write=false` through the recovered
  formal instance.
- In ChatGPT Web, article 2 completed in the same tool call after one extension
  click. The extension ended at green `OK`; the tool returned `status=ok`, title
  `大多数人的估值方法都在预测未来，而预测注定会错`, `characters=5998`,
  `source_channel=rendered_dom`, `network_used=false`, and
  `persistent_write=false`.
- Post-call doctor, exact single-instance checks, and article/token log scans
  passed. Real-article allowance is now fully consumed at 2 of 2; later gates
  must use only fixtures, local health, and lifecycle evidence.

## F5 — upgrade and uninstall: passed

- The first upgrade attempt exposed a launchd convergence race: `bootout`
  returned before the service disappeared, so immediate reinstall correctly
  stopped at `AGENT_ALREADY_LOADED`. The attempt then reached a clean rollback
  state with no label, plist, runtime, logs, process, or port listener.
- The lifecycle now waits with a bounded deadline for launchd to report the
  service absent before cleanup/reinstall. Red/green tests cover delayed
  disappearance and stop timeout; the lifecycle suite has 19 passing tests.
- Automated reinstall evidence confirms the random per-install token changes.
  `doctor` now also compares the private extension config with the current
  token and rejects stale/mismatched configuration.
- The corrected upgrade installed PID `49348`; formal doctor, exact one-process
  check, the MCP-owned `127.0.0.1:18431` listener, and `0600` plist/token/config
  permissions passed.
- After Chrome reloaded the same fixed-ID extension, a no-request pairing probe
  showed blue `WAIT` and then red `TIME` after about 20 seconds, never `AUTH`.
  This proves the rotated token/config pair was accepted while extraction did
  not run because no MCP request was pending.
- The user removed the unpacked extension, then the formal uninstaller removed
  only owned state. Post-uninstall checks found no launchd label, process,
  `127.0.0.1:18431` listener, plist, runtime/token/extension directory, or
  formal log directory.

## F6 — final installation: passed

- Final regression passed: 53 Python tests (two host loopback tests skipped in
  the sandbox run), 6 Node extension tests, syntax compilation, diff checks,
  and proposal policy 1.2 readiness with zero warnings/errors. Both real host
  loopback tests then passed separately.
- Final formal install created PID `50113`; doctor, exact single-instance and
  MCP-owned `127.0.0.1:18431` listener checks passed. Owned directories are
  `0700`; plist, token, generated extension config, and logs are `0600`.
- The user loaded the final private Chrome extension and confirmed version
  `1.0.0` with fixed ID `bpannmkojgebmphkkngpnhkfcgfpnbhn`.
- The final ChatGPT App fixed probe returned `status=ok`,
  `probe_id=gate0-transport-v1`, `fixture=local-mcp-no-network`,
  `network_used=false`, and `persistent_write=false` through PID `50113`.
- Final doctor, exact single-instance/listener checks, private permission checks,
  and article/title/token/config-variable log scans passed. No further real
  article call is allowed.

## Final decision

F0-F6 passed. Proposal `20260918-wechat-reader-l3-full-implementation` is
`verified` for the L3 scope: one user's Mac, ChatGPT App/Web, public WeChat
articles already rendered in the user's Chrome, and one explicit extension
click. This does not verify Windows, public distribution, Chrome Web Store,
cloud article fetching, unattended capture, or multi-user operation.
