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
- Owner-only GitHub identity, explicit browser consent, PKCE S256 and one-time states;
  explicit browser cross-site submissions are rejected and the consent state is browser-bound.
- HTTPS exact-host allowlist: example.com, www.iana.org, mp.weixin.qq.com.
- Fixed Jina POST endpoint, DNT=1, no API key, no automatic retry or provider fallback.
- UTC daily limit: 10 attempts, including failed upstream reads. SQLite Durable Object
  serializes admission and stores the counter across restarts; busy rejections do not count.
- Response maximum 4 MB, upstream deadline 45 seconds. Images remain references; no OCR.
- No article archives or application body logs. KV stores MCP authorization data;
  Durable Object stores quota and short-lived authorization state, not article bodies.
- DNT is a provider request, not a guarantee of zero third-party processing or retention.
  The adapter cannot enforce Jina's internal browser network boundary.

## Current deployment and remaining pilot setup

The validation Worker is deployed at `https://learning-analysis-validation.learning-analysis-worker.workers.dev`.
Its health check, anonymous rejection, OAuth metadata and server-side consent redirect have
passed. The live endpoint is not the production plugin connection and has made zero article
calls.

Before the private pilot:

1. Check the account's Free usage and shared limits; do not add a payment method or upgrade.
2. A dedicated GitHub OAuth App is already configured for this validation Worker:
   homepage = that HTTPS origin; callback = that origin + `/callback`.
   Login requests `read:user`, not repository or email access. Restrict `OWNER_GITHUB_ID`
   to the owner's verified numeric GitHub ID.
3. The Worker has nonsecret `PUBLIC_ORIGIN`, `OWNER_GITHUB_ID`, `GITHUB_CLIENT_ID` configured.
   Store `GITHUB_CLIENT_SECRET` through Workers secret input, never Git or chat.
4. Only use the workers.dev endpoint for this bounded validation.
   Preview URLs remain disabled and no credentials are checked in.
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
