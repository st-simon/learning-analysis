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

## Current route: source-gated hybrid

The preceding setup remains the local baseline. A Cloudflare + Jina SaaS validation Worker was deployed, but a real WeChat article was blocked by upstream environment verification; that route is not the production plugin connection and is frozen at zero Gate 0 requests pending separately approved cleanup. The approved spike direction prioritizes automatic extraction from an already rendered Chrome page through the local MCP and Platform tunnel; users never copy, print or upload article text. Reader direct fetch is only a conditional fast-path probe after its SSH-forwarded backend is identified. See the [project goal](docs/PROJECT_GOAL.md), [architecture](docs/ARCHITECTURE.md), [active proposal](proposals/active/20260914-wechat-reader-hybrid.md), and [validation evidence](docs/cloudflare-validation.md).

The following Python prototype belongs to the earlier self-hosted route. Its tests remain useful as a contract baseline, not as proof that a Workers adapter exists or has passed validation.

`http_server.py` implements stateless HTTP MCP with owner-restricted RS256 token verification. It is a resource server, not an OAuth login service. It requires `READER_ARCHIVE_MODE=none`, canonical HTTPS `MCP_ISSUER_URL` and `MCP_RESOURCE_URL`, an operator-provided public `MCP_PUBLIC_JWKS_FILE`, and `MCP_OWNER_SUBJECTS`. Public-key rotation requires a new configuration/revision. Never use private signing keys for this file. No issuer or production endpoint is configured yet.

Local tests do not prove source reliability. The approved Gate 0 is spike-only: identify the Reader backend, verify App/Web transport with a fixed fixture, test automatic DOM extraction on three current articles, then run the conditional Reader probe. `/healthz` reports process liveness only. Do not call or expose the cloud validation Worker during Gate 0.
