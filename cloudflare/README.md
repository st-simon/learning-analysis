# Private Workers validation adapter

Status: validation Worker deployed; server-side consent probe passed. Real client
authorization and live article verification remain pending.
Existing Python bridge and installed Jina are unchanged. This adapter uses the official
Jina Reader endpoint, not the local Reader. An optional `JINA_API_KEY` Worker Secret avoids
the most restrictive anonymous pool; it is never accepted from the MCP caller. This is not
a production connection switch.

## Reproduce

Node 24; `npm ci --ignore-scripts`, then `npm run verify`.
`npm test` includes unit/mock tests and a loopback-client test. The latter needs
permission to listen on 127.0.0.1. `npm run test:runtime` first bundles with Wrangler
without deployment, then runs one native Workers-runtime integration test. All external
requests in that integration test are intercepted; no article is sent to Jina.
Miniflare is explicitly pinned (currently an alpha dependency of the selected Wrangler).

`npm run probe:client` starts a five-minute loopback receiver and prints a local
page to open manually. It registers one temporary client on the deployed Worker
(a cloud KV write), discovers the authorization endpoint, and uses random PKCE
and state. After GitHub login, it exchanges the code and checks MCP initialize,
initialized notification and tools/list. It never calls read_url. Credentials
stay in memory; output contains only stage/result summaries. The listener closes
on completion, failure, timeout or process termination. Starting it again creates
a new registration; do not use repeated starts as polling.

The older `probe:online` stops at the GitHub redirect and uses a placeholder
callback. Never reuse its registration or fixed verifier for real browser login.
Both live probes create temporary cloud state; they are not read-only checks.
Set `PILOT_URL` only for the approved bounded pilot. It performs one real
`read_url` call after authentication and reports only status and character count.
Do not combine it with automatic retries or an unbounded URL list.

## Boundaries

- One tool: `read_url(url)`, stateless HTTP MCP at `/mcp`.
- Owner-only GitHub identity, explicit browser consent, PKCE S256 and one-time states;
  explicit browser cross-site submissions are rejected and the consent state is browser-bound.
- HTTPS exact-host allowlist: example.com, www.iana.org, mp.weixin.qq.com.
- Fixed Jina POST endpoint, DNT=1, optional server-side API key, no automatic retry or provider fallback.
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
   If Jina's anonymous pool returns 429, confirm a no-payment Jina Reader API key is available,
   then set it interactively with `npx wrangler secret put JINA_API_KEY`; never put the value in
   shell history, source files, `.dev.vars`, logs or chat. The key is optional in local tests but
   required to validate recovery from shared-egress anonymous throttling.
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
