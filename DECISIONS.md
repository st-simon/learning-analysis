# Decisions
- Hybrid: local Jina extraction, ChatGPT analysis; no Google OAuth flow.
- FastMCP stdio avoids another HTTP listener; tunnel-client forwards to the local process.
- Narrow exact host allowlist, public DNS check, 4 MB response cap, no automatic retries, private content-addressed archive.
- The host allowlist is a staged product-security policy, not a claim about all technically readable sites. Add domains only when there is a concrete need; evaluate each domain independently for security, privacy, reliability, extraction quality, and operational cost; allow the smallest necessary scope; and verify it before inclusion.
