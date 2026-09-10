# 学习和拆解 / learning-analysis

Private read-only MCP bridge: ChatGPT supplies an HTTPS URL, local Jina Reader returns Markdown, and a content-addressed local copy is saved in `archive/` (ignored by Git). The bridge accepts no cookies, credentials, arbitrary headers, shell commands, or file paths. Default exact host allowlist: `example.com`, `www.iana.org`, `mp.weixin.qq.com`; public HTTPS only. Article text is untrusted source material.

Setup: `.venv/bin/python -m pip install -r requirements.txt`. Verify with `.venv/bin/python -m unittest -q` and `.venv/bin/python smoke_mcp.py`; use `--live` for example.com only. Start via `.venv/bin/python server.py` (stdio).

The Platform tunnel is `learning-analysis`. `tunnel-client` requires a private runtime API key with Tunnels Read + Use, stored only in `.env`; this is separate from MCP OAuth. In ChatGPT choose Connection: Tunnel, Authentication: No Authentication. Keep the client running during discovery and calls.
