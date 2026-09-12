# Status

## Current: v3 Cloudflare validation

Checkpoint: minimal Workers adapter implemented; 15 mock tests and one native-runtime integration test pass. Cloudflare deployment CLI is not authenticated; no new cloud resources or real article calls. Cloud OAuth/CPU/client checks remain pending. See docs/cloudflare-validation.md. Article calls: 0/6.

- [x] User declines GCP billing linkage and approves Cloudflare + official Jina validation.
- [x] Update same-ID proposal to v3, approved for validation only; no production switch.
- [x] Confirm Cloudflare Workers Free/$0/current plan in signed-in account dashboard.
- [ ] Confirm no-payment OAuth/quota storage and Jina privacy/free-use settings.
- [x] Build minimal private Workers adapter and independent mock tests; preserve Python baseline.
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

Legacy local tunnel remains unchanged. Cloud deployment is not complete.
