# Cloudflare v3 validation — updated 2026-09-13

## Result: local adapter verified; cloud authorization pending

2026-09-13: implemented `cloudflare/` with 15 passing unit/mock tests plus one passing
native Workers-runtime integration test. The latter verifies the full mocked GitHub/OAuth
flow, private MCP tools, 10 successful mocked reads, rejection of the 11th after runtime
recreation, and concurrent admission. Wrangler dry-run packaging passed; npm audit found
zero known vulnerabilities at installation time. No deployment occurred.

Runtime validation found and fixed an unsupported fetch redirect option in the adapter.
It also corrected the test harness's redirect handling and Miniflare persistence settings.
Temporary diagnostic logging was removed. Configuration remains fail-closed, with disabled
public/preview endpoints and a placeholder KV ID. Real CPU limits and client compatibility
are not established by these local tests.

Read-only `wrangler whoami` reports not authenticated. Browser dashboard login does not
authorize the deployment CLI. Next requires deployment authorization and a dedicated
owner-only GitHub OAuth App; never send client secrets in chat. No temporary deployment
account, payment method, upgrade, production switch, or real Jina call was used.

## Historical account checkpoint (2026-09-12)

Follow-up: the connected Chrome shows the signed-in personal account. Workers plans page visibly shows `Free`, `$0 For personal use and simple applications`, and `Current plan`. The account/plan prerequisite is therefore confirmed by the user-visible dashboard. No upgrade, payment method, Worker, binding or article call was performed.

The approved validation has started. An earlier dashboard load timed out, but the existing signed-in Chrome window was then brought to the foreground and the account page loaded. The selected Workers Free plan visibly lists 100,000 requests/day, 10 ms CPU/request, 50 subrequests/request, and 100 Workers/account. The same page lists Free Durable Objects limits of 100,000 requests/day, 13,000 GB-s/day, 5,000,000 SQL rows read/day, 100,000 rows written/day and 5 GB stored data. These are account-plan figures, not measured remaining quota.

## Documentation evidence (not account verification)

- Workers KV includes limited Free usage, currently 100,000 reads/day and 1,000 writes/day. Authentication storage may fit, subject to the selected implementation and shared account usage. [Pricing](https://developers.cloudflare.com/kv/platform/pricing/), [limits](https://developers.cloudflare.com/kv/platform/limits/).
- SQLite-backed Durable Objects are available on Workers Free. The adapter uses one SQLite-backed object for persistent daily request counting and short-lived auth state; local concurrency and reconstructed-runtime behavior passed, while cloud quota behavior remains unverified. Free accounts cannot use the legacy KV-backed Durable Objects backend. [Pricing](https://developers.cloudflare.com/durable-objects/platform/pricing/).
- Cloudflare documents a remote MCP GitHub OAuth template using a workers.dev endpoint. This is a candidate login route, not an already-configured authorization server. Owner restriction, permissions, token/resource validation, free resource footprint and client compatibility remain to be checked. Creating a GitHub OAuth App or granting access requires the corresponding user action/approval. [Official guide](https://developers.cloudflare.com/agents/model-context-protocol/guides/remote-mcp-server/).

These findings support continuing feasibility assessment, not a claim that the whole authenticated service is proven free or ready. No dependency was installed and no new code was deployed in this checkpoint.

## Test ledger

- Real article calls: 0 / 6 authorized for the initial pilot.
- Workers mocks: 15 unit tests plus 1 native-runtime integration test passed. Cloud CPU and real authentication/client compatibility remain unverified.
- Actual Cloudflare account/plan: Free/$0/current plan confirmed in the dashboard; remaining usage and account-wide consumption not inspected.
- Jina privacy settings and live extraction: pending; no article transmitted.
- Existing Python baseline: prior 13 tests and stdio smoke, not rerun or counted as Workers validation.
- Production plugin connection and local Jina: unchanged.

## Required next action

Authorize the deployment CLI and prepare the dedicated GitHub OAuth App; then inspect required Free usage/features and deploy only the authenticated private test endpoint. Do not add a payment method or upgrade. Real OAuth, cloud quota behavior, Jina extraction and privacy behavior remain open. Do not retry article access or switch providers to work around site restrictions.
