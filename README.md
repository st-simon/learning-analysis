# 学习和拆解 / learning-analysis

Private browser-assisted MCP bridge for public WeChat articles. ChatGPT calls
`read_rendered_url`, the local MCP waits in memory, and one explicit Chrome
extension click extracts the already-rendered article DOM. The formal route
does not fetch the article again, persist its body, upload cookies, or fall back
to Jina/Cloudflare. Article text is always untrusted source material.

## Domain allowlist policy

The host allowlist is a staged product-security boundary, not a complete list of sites that Jina can technically read. It remains intentionally narrow while the bridge is being validated. Add a domain only when there is a concrete requirement, and evaluate it independently before inclusion:

- security and network boundary risks;
- privacy and data-handling implications;
- access reliability and failure behavior;
- extraction quality for the intended pages; and
- operational cost and maintenance burden.

Each addition must use the smallest necessary host scope, pass a focused verification, and be documented as a deliberate product decision. Do not expand the allowlist merely because a single URL failed or because a site is technically readable.

Setup: `.venv/bin/python -m pip install -r requirements.txt`. Verify with
`.venv/bin/python -m unittest -q`. Install and supervise the formal local route
with `.venv/bin/python learning_analysis_lifecycle.py install`.

The Platform tunnel is `learning-analysis`. `tunnel-client` requires a private
runtime API key with Tunnels Read + Use, stored only in `.env`; this is separate
from MCP OAuth. The user LaunchAgent keeps the client and stdio MCP running.

## Current route: browser-first L3 implementation

The approved [L3 full-implementation proposal](proposals/active/20260918-wechat-reader-l3-full-implementation.md) is verified. F0-F6 passed: in-process capture runtime, formal LaunchAgent, private extension/token, bounded doctor, App/Web transport, two current articles, natural login recovery in about 13.4 seconds, token-rotating upgrade, zero-residue uninstall, and final reinstall. The Reader direct-fetch probe remains inconclusive and the Cloudflare + Jina SaaS validation Worker remains frozen. See the [implementation evidence](docs/l3-full-implementation-evidence.md), [project goal](docs/PROJECT_GOAL.md), and [architecture](docs/ARCHITECTURE.md).

Formal local lifecycle commands:

```text
.venv/bin/python learning_analysis_lifecycle.py status --wait 45
.venv/bin/python learning_analysis_lifecycle.py doctor --wait 45
.venv/bin/python learning_analysis_lifecycle.py upgrade
.venv/bin/python learning_analysis_lifecycle.py uninstall
```

The generated unpacked extension directory is
`runtime/learning-analysis/extension`. It is private runtime state and must not
be committed or shared.

The following Python prototype belongs to the earlier self-hosted route. Its tests remain useful as a contract baseline, not as proof that a Workers adapter exists or has passed validation.

`http_server.py` implements stateless HTTP MCP with owner-restricted RS256 token verification. It is a resource server, not an OAuth login service. It requires `READER_ARCHIVE_MODE=none`, canonical HTTPS `MCP_ISSUER_URL` and `MCP_RESOURCE_URL`, an operator-provided public `MCP_PUBLIC_JWKS_FILE`, and `MCP_OWNER_SUBJECTS`. Public-key rotation requires a new configuration/revision. Never use private signing keys for this file. No issuer or production endpoint is configured yet.

Local tests do not prove source reliability. Gate 1A-R and disposable Gate 1B evidence are complete; Gate 1B used zero article calls and zero Cloudflare/Jina use, then removed its runtime. `/healthz` reports process liveness only; readiness, control-plane polling, tool discovery and a fixed call remain separate gates.
