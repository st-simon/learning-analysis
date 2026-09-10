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
