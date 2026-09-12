# Private Workers validation adapter

Status: local mock verification only. No cloud deployment or live article verification yet.
Existing Python bridge and installed Jina are unchanged. This adapter uses the official
anonymous Jina Reader endpoint, not the local Reader. It is not a production connection switch.

## Reproduce

Node 24; `npm ci --ignore-scripts`, then `npm run verify`.
`npm test` runs 15 unit/mock tests. `npm run test:runtime` first bundles with Wrangler
without deployment, then runs one native Workers-runtime integration test. All external
requests in that integration test are intercepted; no article is sent to Jina.
Miniflare is explicitly pinned (currently an alpha dependency of the selected Wrangler).

## Boundaries

- One tool: `read_url(url)`, stateless HTTP MCP at `/mcp`.
- Owner-only GitHub identity, explicit browser consent, PKCE S256 and one-time states.
- HTTPS exact-host allowlist: example.com, www.iana.org, mp.weixin.qq.com.
- Fixed Jina POST endpoint, DNT=1, no API key, no automatic retry or provider fallback.
- UTC daily limit: 10 attempts, including failed upstream reads. SQLite Durable Object
  serializes admission and stores the counter across restarts; busy rejections do not count.
- Response maximum 4 MB, upstream deadline 45 seconds. Images remain references; no OCR.
- No article archives or application body logs. KV stores MCP authorization data;
  Durable Object stores quota and short-lived authorization state, not article bodies.
- DNT is a provider request, not a guarantee of zero third-party processing or retention.
  The adapter cannot enforce Jina's internal browser network boundary.

## Account setup needed before private pilot

1. Authorize the deployment tool for the intended Cloudflare Free account. Review requested
   permissions in the browser; do not use a temporary account or select a paid plan.
2. Create this project's OAuth KV namespace and SQLite Durable Object binding only.
   Replace the placeholder namespace ID. Record exact resource IDs privately for rollback.
3. Reserve the private test Worker origin and create a dedicated GitHub OAuth App:
   homepage = that HTTPS origin; callback = that origin + `/callback`.
   Login requests `read:user`, not repository or email access. Restrict `OWNER_GITHUB_ID`
   to the owner's verified numeric GitHub ID.
4. Configure nonsecret `PUBLIC_ORIGIN`, `OWNER_GITHUB_ID`, `GITHUB_CLIENT_ID`.
   Store `GITHUB_CLIENT_SECRET` through Workers secret input, never Git or chat.
5. Only enable the test workers.dev endpoint once authentication/configuration is ready.
   The checked-in config disables workers.dev and preview URLs and has no credentials.
   `/healthz` means the process is alive, not that Reader extraction has been verified.
6. Verify real client authorization and anonymous rejection before any real article call.
   Check Free CPU/KV/DO usage and account-shared limits. Local runtime speed is not proof
   that cloud execution fits the Free CPU allowance.
7. Follow the proposal's six-call pilot ledger. Stop on CAPTCHA, restriction or quota failure;
   never automatically retry. Overnight and cross-device checks remain separate acceptance.

Public OAuth registration is necessary for the selected dynamic-client flow and can consume
KV writes even without article access. Registration expiry and a 16-flow admission cap bound
stored state, but do not guarantee abuse resistance or uninterrupted Free availability.
Review this exposure and actual client compatibility before production approval.

Rollback: disable only this test endpoint and revoke its own authorization credentials.
Do not delete existing local Reader resources or alter the production plugin connection.
