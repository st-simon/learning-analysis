# 学习和拆解 / learning-analysis

Private read-only MCP bridge: ChatGPT supplies an HTTPS URL, local Jina Reader returns Markdown, and a content-addressed local copy is saved in `archive/` (ignored by Git). The bridge accepts no cookies, credentials, arbitrary headers, shell commands, or file paths. Default exact host allowlist: `example.com`, `www.iana.org`, `mp.weixin.qq.com`; public HTTPS only. Article text is untrusted source material.

## Domain allowlist policy

The host allowlist is a staged product-security boundary, not a complete list of sites that Jina can technically read. It remains intentionally narrow while the bridge is being validated. Add a domain only when there is a concrete requirement, and evaluate it independently before inclusion:

- security and network boundary risks;
- privacy and data-handling implications;
- access reliability and failure behavior;
- extraction quality for the intended pages; and
- operational cost and maintenance burden.

Each addition must use the smallest necessary host scope, pass a focused verification, and be documented as a deliberate product decision. Do not expand the allowlist merely because a single URL failed or because a site is technically readable.

Setup: `.venv/bin/python -m pip install -r requirements.txt`. Verify with `.venv/bin/python -m unittest -q` and `.venv/bin/python smoke_mcp.py`; use `--live` for example.com only. Start via `.venv/bin/python server.py` (stdio).

The Platform tunnel is `learning-analysis`. `tunnel-client` requires a private runtime API key with Tunnels Read + Use, stored only in `.env`; this is separate from MCP OAuth. In ChatGPT choose Connection: Tunnel, Authentication: No Authentication. Keep the client running during discovery and calls.

## Current route: browser-first L3 readiness

Gate 0 proved the browser-first route with 3/3 real articles and a real App/Web round trip through the Platform tunnel. Gate 1A-R then verified exact extension pairing, bounded early/late-click coordination, machine-checked tunnel readiness, and one successful App article call with one browser click. Gate 1B verified a disposable user-level LaunchAgent: initial and post-recovery App probes were routed by the expected instances, one controlled kill recovered to a new healthy PID, secrets and article data stayed out of plist/logs, and uninstall left zero runtime residue. The Reader direct-fetch probe remains inconclusive and the Cloudflare + Jina SaaS validation Worker remains frozen. Full implementation is not yet authorized; Gate 1B does not make the capture bridge persistent or prove natural login/restart startup. See the [project goal](docs/PROJECT_GOAL.md), [architecture](docs/ARCHITECTURE.md), [Gate 1B evidence](docs/gate1b-lifecycle-evidence.md), [Gate 1A-R evidence](docs/gate1a-race-fix-evidence.md), and [historical Cloudflare evidence](docs/cloudflare-validation.md).

The following Python prototype belongs to the earlier self-hosted route. Its tests remain useful as a contract baseline, not as proof that a Workers adapter exists or has passed validation.

`http_server.py` implements stateless HTTP MCP with owner-restricted RS256 token verification. It is a resource server, not an OAuth login service. It requires `READER_ARCHIVE_MODE=none`, canonical HTTPS `MCP_ISSUER_URL` and `MCP_RESOURCE_URL`, an operator-provided public `MCP_PUBLIC_JWKS_FILE`, and `MCP_OWNER_SUBJECTS`. Public-key rotation requires a new configuration/revision. Never use private signing keys for this file. No issuer or production endpoint is configured yet.

Local tests do not prove source reliability. Gate 1A-R and disposable Gate 1B evidence are complete; Gate 1B used zero article calls and zero Cloudflare/Jina use, then removed its runtime. `/healthz` reports process liveness only; readiness, control-plane polling, tool discovery and a fixed call remain separate gates.
