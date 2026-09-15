# Status

## Current: hybrid source-gated route

Checkpoint: Proposal policy 1.2 Gate 0 spike was approved on 2026-09-16. The Cloudflare + Jina SaaS fetch route is superseded by real anti-bot evidence; its deployed validation resources remain frozen at zero Gate 0 requests pending explicit cleanup approval.

- [x] Record Jina SaaS rate-limit and WeChat environment-verification evidence.
- [x] Stop treating Cloudflare + Jina SaaS as the production fetch route.
- [x] Define the automatic-browser/conditional-Reader architecture and Gate 0.
- [x] Obtain approval to implement the bounded Gate 0 spike.
- [ ] Receive 3 current WeChat article URLs from the user.
- [ ] H0: identify the SSH-forwarded Reader backend without an article call; skip H1 if it remains unknown.
- [ ] H3a/H3b: verify ChatGPT App/Web fixed-fixture transport through Platform tunnel; do not call Worker.
- [ ] H2: automatically extract the already rendered DOM for 3 articles, once each, with no content copying.
- [ ] H3c: return one H2 article through local MCP and Platform tunnel to App/Web.
- [ ] H1: test 1 direct Reader article only after H0; continue to 2 more only if the first succeeds.
- [ ] Record structured evidence and stop for a new full-implementation proposal decision.
- [ ] Obtain separate approval before plugin switching or cloud credential/resource cleanup.

## Superseded: v3/v4 Cloudflare validation

Closed without completing the remaining pilot gates. The list below is retained as historical scope, not current work.

Checkpoint: minimal Workers adapter implemented; 15 mock tests and one native-runtime integration test pass. Free KV and validation Worker deployed; health/anonymous/OAuth metadata/server-side consent checks pass. Real token exchange, cloud CPU/client checks and article calls remain pending. See docs/cloudflare-validation.md. Article calls: 0/6.

- [x] User declines GCP billing linkage and approves Cloudflare + official Jina validation.
- [x] Update same-ID proposal to v3, approved for validation only; no production switch.
- [x] Confirm Cloudflare Workers Free/$0/current plan in signed-in account dashboard.
- [ ] Confirm no-payment OAuth/quota storage and Jina privacy/free-use settings.
- [x] Build minimal private Workers adapter and independent mock tests; preserve Python baseline.
- [x] Deploy authenticated validation Worker and verify health, anonymous rejection, OAuth metadata and consent redirect.
- [ ] Run bounded article/first/continuous/overnight checks and report evidence under v3.
- [ ] Obtain production-switch confirmation after validation; verify two devices and rollback.

## Historical v2 / local baseline (GCP deployment on hold)
- [x] Platform tunnel created and visible in ChatGPT.
- [x] Read-only MCP bridge and focused tests.
- [x] Receive v2 approval, project ID reading-analysis-508317 and reading volume.
- [x] Local stateless HTTP adapter, token validation, no-archive mode and worker deadline tests (13 tests).
- [x] User confirms Chrome sign-in and no active billing account linked.
- [ ] Billing gate: user decision on account linkage versus no-billing-account alternative; shared free allowances not yet verified.
- [ ] Select and verify a compatible free OAuth provider; local JWT tests are not a complete login flow.
- [ ] Pin Reader build and verify browser egress/metadata isolation, memory and cold start.
- [ ] Implement durable usage limits; measure image/build/network/auth costs before deployment.
- [ ] Deploy only after free/security gates pass; verify actual article and cross-device calls.
- [ ] Switch exact private plugin connection with rollback; no public unauthenticated reader.

Legacy local tunnel remains unchanged. The validation Worker exists but is not the production plugin connection.
