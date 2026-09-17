# Gate 1A-R race-fix evidence

Date: 2026-09-17
Proposal: `20260917-wechat-reader-gate1a-race-fix`
Status: verified. R0-R2 and P15 passed; the renewed R3 passed in one App call and one extension click; final cleanup and regression verification passed.

2026-09-18 amendment: the user approved a narrow rerun only after four machine-verifiable tunnel gates pass: expected process identity, successful control-plane poll, health/ready on that same instance, and one App `gate0_transport_probe` observed locally. One new real-article attempt is restored only after P15 passes.

## Baseline

- Baseline commit pushed before implementation: `9a47524`.
- Reproduced defect: before the fix, `GET /pending` returned the generic `NOT_FOUND`; the existing capture endpoint rejected a submission made before `CaptureCoordinator.begin()` with `CAPTURE_NOT_FOUND`.
- The prior App attempt had entered the 25-second MCP wait but accepted no capture, ending in `CAPTURE_TIMEOUT` and a generic extension `ERR` badge.

## P11

Assumption: an early click can wait until pending exists, then extract and submit exactly once; a late click proceeds immediately.

Implemented seam:

- Authenticated `GET /pending?url=...` returns only `PENDING_READY` or `NO_PENDING`.
- The extension waits at most 20 seconds, polling every 250 ms.
- Article extraction runs only after `PENDING_READY`; no article body is sent or buffered during readiness polling.
- The terminal badge is one of `OK`, `PAGE`, `AUTH`, `URL`, `TIME`, or `SEND`.

Evidence:

- Red signal: focused Python test failed with `NOT_FOUND` before `/pending` existed.
- Green signal: focused Python readiness test passed after the minimal endpoint was added.
- Red signal: Node test failed because `runCaptureFlow` did not exist.
- Green signal: six Node tests passed for URL validation, early click, late click, bounded timeout, auth classification, and exactly-once extract/submit ordering.
- Full Python suite: 30 tests passed, 1 opt-in loopback test skipped in the default sandbox run.
- Real loopback integration outside the restricted socket sandbox: 1 test passed. It observed `NO_PENDING`, started the MCP waiter, observed `PENDING_READY`, submitted once, and returned the article to the same waiter.
- MCP smoke: passed handshake, no-network probe, read-only discovery, and unsafe URL rejection.

Decision: `passed` for R0 / P11.

## P12

Assumption: the readiness endpoint preserves the existing trust boundary and does not expose sensitive data.

Evidence:

- Wrong extension Origin: HTTP 403 `FORBIDDEN_ORIGIN`.
- Wrong installation token: HTTP 401 `UNAUTHORIZED`.
- Non-WeChat URL: HTTP 400 `INVALID_SOURCE_URL`.
- Ready response body is exactly `{"status": "PENDING_READY"}`; it does not include request ID, URL, title, article body, token, or stack trace.
- `BaseHTTPRequestHandler.log_message` remains suppressed; new implementation adds no diagnostic logging.
- Manifest identity test passed and permissions remain exactly `activeTab`, `scripting`, and `http://127.0.0.1:18431/*`.

Real-browser contradiction:

- The unpacked extension loaded in the Jun Chrome profile as version `0.1.1` with the expected ID `bpannmkojgebmphkkngpnhkfcgfpnbhn`.
- The generated extension config and bridge token matched; a host-side request with the same expected Origin and token returned `404 {"status":"NO_PENDING"}` as designed.
- Three real extension `GET /pending` attempts returned HTTP 403 `FORBIDDEN_ORIGIN`.
- The redacted server event recorded `request_method=GET` and `origin_class=MISSING`; no URL, Origin value, token, body, or stack was logged.
- The extension displayed the stage-specific `AUTH` badge, proving that the new error classification worked.

Decision: automated R1 security matrix passed, but P12 is `failed` because the original exact-Origin model is incompatible with the actual Chrome 152 service-worker request. H12 remains a recorded contradiction; dependent work resumed only after the user approved the narrower H14 identity amendment.

## P10

The extension version `0.1.2` loaded with the expected stable ID and did not request new permissions. With no MCP pending request, one real Chrome click displayed blue `WAIT`, remained alive for approximately 20 seconds, and then changed to the stage-specific red `TIME` terminal state. No page extraction or capture submission occurs before readiness, so this fixture transmitted no article body.

Decision: `passed` for H10 and Gate R2. The current Chrome extension service worker retained `activeTab` authority and completed the bounded readiness loop without broader permissions or a generic error.

## P13

One App attempt used the user-selected public article. The App returned the reduced error contract, while the extension displayed blue `WAIT` and then red `TIME` after the bounded wait.

Post-attempt read-only evidence:

- The loopback bridge was listening throughout the attempt.
- No `tunnel-client` process or TCP connection to the OpenAI control plane was present.
- The bridge emitted no timeout/error event for an MCP `GET /capture` wait request; therefore the App invocation never registered pending state in this bridge.
- The extension's `WAIT` → `TIME` result is consistent with repeatedly receiving `NO_PENDING`; it does not falsify the amended extension authentication or waiting logic already proven by R2.
- The pre-R3 check verified only the bridge, token, generated extension config, and Git state. It omitted the proposal's required Platform tunnel liveness check. This was an execution-procedure defect.

Decision: the single R3 attempt is `failed` at the environment-precondition gate and H13 remains `inconclusive`; it is not evidence that same-call capture fails when the tunnel is live. The approved no-retry rule still requires the proposal to stop as `blocked`. Any rerun requires a new or amended proposal with a machine-verifiable tunnel preflight before consuming the real-article attempt.

Renewed attempt after the approved P15 amendment:

- The user selected one new public WeChat article and confirmed it was fully rendered in the Jun Chrome profile.
- Immediately before the attempt, the same tunnel instance again passed PID, control-plane poll, `/healthz`, and `/readyz`; the bridge was listening only on `127.0.0.1:18431`.
- In the same ChatGPT App conversation that passed the fixed probe, one `read_rendered_url` call plus one extension click returned `status=ok`, title `我给爆火的261种手绘风格加了个Router✨`, `characters=1671`, `source_channel=rendered_dom`, `network_used=false`, and `persistent_write=false`.
- The extension displayed green `OK`.
- Local tunnel evidence recorded one `CallToolRequest`; the MCP process received HTTP 200 from the loopback bridge and completed `rendered_capture` successfully in about 5.9 seconds.
- No retry, Web test, `read_url`, Jina, or Cloudflare call occurred.

Decision: `passed` for the renewed P13/H13 validation. The user-visible same-call, one-click outcome is verified for this bounded App sample.

## P14

The user approved the amended identity contract after H12 was contradicted:

- Every extension readiness and capture request sends public `chrome.runtime.id` in `X-Learning-Analysis-Extension-Id`.
- A non-empty Origin must still match the fixed extension origin exactly.
- An absent Origin is accepted only when the extension ID header matches and the random per-install token authenticates.
- Missing/wrong extension ID, wrong token, and any non-empty web Origin remain rejected.

Automated evidence after the amendment:

- 34 Python tests passed; one opt-in socket test was skipped in the default sandbox run.
- 6 Node tests passed, including the exact extension ID header on every readiness poll.
- MCP smoke passed.
- The opt-in real loopback integration passed with no Origin, the exact extension ID header, and token for both readiness and capture.
- Proposal readiness checker passed with no warnings or errors.

Real Chrome evidence after reload:

- The Jun-profile extension reported the same stable ID at version `0.1.2`.
- With no Origin header, the exact extension ID header and installation token passed the bridge identity gate.
- The user observed blue `WAIT` followed approximately 20 seconds later by red `TIME`, rather than `AUTH`.
- The expected no-pending path did not expose or persist article content.

Decision: `passed` for H14. The amended identity contract works in the actual Chrome request shape while the automated matrix continues to reject missing/wrong ID, wrong token, and incorrect non-empty Origin combinations.

## P15

In progress on 2026-09-18. The amended preflight uses tunnel-client PID and health URL files plus `tunnel-client health --require-control-plane-poll --json` for the first three gates.

Observed evidence:

- The expected tunnel-client `0.0.14` instance wrote a PID file, and the official health command confirmed that PID was running.
- The same command resolved the instance through its generated loopback health URL and returned HTTP 200 `live` from `/healthz` and HTTP 200 `ready` from `/readyz`.
- `--require-control-plane-poll` reported a successful control-plane poll for that instance.
- An initial check inside the Codex sandbox could not connect to loopback (`operation not permitted`); the unchanged read-only command passed in the Mac host network environment. The sandbox result is recorded as an execution-environment limitation, not a tunnel failure.

Fourth-gate evidence:

- A new ChatGPT desktop App conversation returned the exact fixed result: `status=ok`, `probe_id=gate0-transport-v1`, `fixture=local-mcp-no-network`, `network_used=false`, and `persistent_write=false`.
- The same tunnel instance recorded `Processing request of type CallToolRequest` and forwarded the command to its local MCP server at the matching time.

Decision: `passed` for P15/H15. All four preflight gates belong to the same active tunnel instance. Only after this result may the temporary bridge/config and extension be restored for the single renewed R3 attempt.

Immediately before requesting the renewed R3 article URL, the user confirmed extension version `0.1.2` and the fixed ID. A fresh machine check again reported the same tunnel PID running, HTTP 200 `live`, HTTP 200 `ready`, and a successful control-plane poll; the memory-only bridge was listening only on `127.0.0.1:18431`, with both ignored pairing files present.

## Cleanup and current temporary state

- After the first contradiction, the temporary loopback bridge was stopped and the token/config files were deleted without printing their contents.
- For the approved amendment and R2/R3 runs, the temporary bridge, token, and generated config were recreated.
- After the first failed R3 attempt, the bridge and pairing files were cleaned and the user removed the extension.
- After the renewed successful R3 attempt, the tunnel and bridge were stopped cleanly.
- The user explicitly approved deletion of the four ignored pairing/runtime files and confirmed manual removal of the unpacked extension.
- Final cleanup verification found all four files absent, ports `18431` and the tunnel admin port not listening, and no tunnel-client connection detected.
- Final regression verification: 21 Python unittest cases passed with 1 opt-in socket test skipped in the sandbox, 6 Node flow tests passed, MCP smoke passed, proposal readiness passed with no warnings/errors, and `git diff --check` passed.
