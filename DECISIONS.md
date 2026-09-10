# Decisions
- Hybrid: local Jina extraction, ChatGPT analysis; no Google OAuth flow.
- FastMCP stdio avoids another HTTP listener; tunnel-client forwards to the local process.
- Narrow exact host allowlist, public DNS check, 4 MB response cap, no automatic retries, private content-addressed archive.
