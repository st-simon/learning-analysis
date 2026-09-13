# Cloudflare v3 validation — updated 2026-09-13

## Result: validation Worker deployed; live client/article verification pending

2026-09-13: implemented `cloudflare/` with 15 passing unit/mock tests plus one passing
native Workers-runtime integration test. The latter verifies the full mocked GitHub/OAuth
flow, private MCP tools, 10 successful mocked reads, rejection of the 11th after runtime
recreation, and concurrent admission. Wrangler dry-run packaging passed; npm audit found
zero known vulnerabilities at installation time. The Free KV namespace and validation Worker
were later deployed; no article call occurred.

Runtime validation found and fixed an unsupported fetch redirect option in the adapter.
It also corrected the test harness's redirect handling and Miniflare persistence settings.
Temporary diagnostic logging was removed. The validation Worker now has workers.dev enabled,
owner-only GitHub OAuth configuration and an isolated short-lived auth-state partition. Real
CPU limits, token exchange completion and MCP client compatibility remain unverified.

Wrangler authorization, the dedicated owner-only GitHub OAuth App, and the encrypted Worker
secret are configured. A server-side OAuth form check returned 302 to GitHub; browser-driven
token exchange and MCP client compatibility remain pending. No temporary deployment account,
payment method, upgrade, production switch, or real Jina call was used.

## Historical account checkpoint (2026-09-12)

Follow-up: the connected Chrome shows the signed-in personal account. Workers plans page visibly shows `Free`, `$0 For personal use and simple applications`, and `Current plan`. The account/plan prerequisite is therefore confirmed by the user-visible dashboard. No upgrade, payment method, Worker, binding or article call was performed.

The approved validation has started. An earlier dashboard load timed out, but the existing signed-in Chrome window was then brought to the foreground and the account page loaded. The selected Workers Free plan visibly lists 100,000 requests/day, 10 ms CPU/request, 50 subrequests/request, and 100 Workers/account. The same page lists Free Durable Objects limits of 100,000 requests/day, 13,000 GB-s/day, 5,000,000 SQL rows read/day, 100,000 rows written/day and 5 GB stored data. These are account-plan figures, not measured remaining quota.

## Documentation evidence (not account verification)

- Workers KV includes limited Free usage, currently 100,000 reads/day and 1,000 writes/day. Authentication storage may fit, subject to the selected implementation and shared account usage. [Pricing](https://developers.cloudflare.com/kv/platform/pricing/), [limits](https://developers.cloudflare.com/kv/platform/limits/).
- SQLite-backed Durable Objects are available on Workers Free. The adapter uses one SQLite-backed object for persistent daily request counting and short-lived auth state; local concurrency and reconstructed-runtime behavior passed, while cloud quota behavior remains unverified. Free accounts cannot use the legacy KV-backed Durable Objects backend. [Pricing](https://developers.cloudflare.com/durable-objects/platform/pricing/).
- Cloudflare documents a remote MCP GitHub OAuth template using a workers.dev endpoint. This is a candidate login route, not an already-configured authorization server. Owner restriction, permissions, token/resource validation, free resource footprint and client compatibility remain to be checked. Creating a GitHub OAuth App or granting access requires the corresponding user action/approval. [Official guide](https://developers.cloudflare.com/agents/model-context-protocol/guides/remote-mcp-server/).

These findings support continuing feasibility assessment, not a claim that the whole
authenticated service is proven free or ready. The deployed Worker remains a validation
endpoint, not the production plugin connection.

## Test ledger

- Real article calls: 0 / 6 authorized for the initial pilot.
- Workers mocks: 15 unit tests plus 1 native-runtime integration test passed. Health check,
  anonymous MCP 401, OAuth metadata and server-side OAuth consent 302 passed online. Cloud
  CPU, token exchange and real MCP client compatibility remain unverified.
- Actual Cloudflare account/plan: Free/$0/current plan confirmed in the dashboard; remaining usage and account-wide consumption not inspected.
- Jina privacy settings and live extraction: pending; no article transmitted.
- Existing Python baseline: prior 13 tests and stdio smoke, not rerun or counted as Workers validation.
- Production plugin connection and local Jina: unchanged.

## Required next action

Browser consent finding: Chrome console explicitly reported a form-action 'self'
CSP violation after the consent submission. Replaced the external POST redirect
with a same-origin 200 continuation page linking to GitHub; kept the CSP unchanged.
Added fixed, nonsecret consent error categories. 17 unit/mock tests and native
runtime passed. Deployment c37420e6-1862-4a62-bbed-818b16eb2d52 was verified in
Chrome Jun: consent succeeds and the GitHub authorization page is reached.
GitHub final authorization, real token exchange and tool discovery remain pending.
The older 302 probe results below are historical; successful consent now returns 200.

OAuth navigation regression: the global cross-site check rejected legitimate GET
requests to /authorize and /callback. A native-runtime test reproduced 403 before
the fix and passed after exempting only those two GET entry points. Cross-site
POST and MCP requests remain rejected; callback cookie/state/owner checks remain.
Validation deployment 4182cbd6-7202-432b-bb73-d907a792b930 passed an online
cross-site-header consent probe (200 then 302). Real browser callback/token and
article verification are still pending. The earlier ERR_BLOCKED_BY_CLIENT
observation has not been attributed to this separate application 403.

The real client harness is now `cd cloudflare && npm run probe:client`. Its
local mocked regression verifies state rejection, PKCE binding, token exchange,
initialize/initialized/tools-list ordering, and zero article calls. This is
local evidence only until a human completes the deployed GitHub flow.

Correction to earlier diagnosis: ERR_BLOCKED_BY_CLIENT was observed during
automated browser navigation; its precise source is not established. The previous
probe's example.com callback could not receive a real client authorization result.
The new client registers a loopback callback instead. No browser protections were
disabled and no deployed Worker change was required for this harness.

Complete a real client token exchange against the deployed endpoint, then inspect required
Free usage/features before any article call. Do not add a payment method or upgrade. Real
Jina extraction and privacy behavior remain open; after client verification, follow the
proposal's maximum six-call article pilot. Do not retry article access or switch providers
to work around site restrictions.
