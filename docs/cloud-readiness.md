# Cloud migration readiness — 2026-09-12

## Current route: proposal v3 approved for validation

Latest checkpoint: signed-in Cloudflare account visibly shows Workers Free/$0/current plan and published free limits. See [validation record](cloudflare-validation.md). No article calls or deployment yet.

User declines GCP billing linkage and approves validating Cloudflare Workers Free + Jina official Reader; this turn updates the proposal first. No Workers deployment, real-article validation or production connection switch has happened. The v3 proposal is authoritative; the GCP compute illustration and deployment gates below are historical v2 evidence, not the current deployment plan.

Next: check Cloudflare Free account access and a no-payment authentication/quota path, then build a minimal private adapter and mock tests. Only after the gates pass, run at most six real article calls under v3's no-retry rules and report extraction, image-reference fidelity and first/continuous/overnight timing. Formal plugin switching requires separate confirmation. The user need not link GCP billing or send secrets.

## Confirmed inputs

- Approved proposal v2; project: `reading-analysis-508317`.
- Personal research: 0–10 articles/day, average 3–4; 90–120 per 30-day month, maximum 300 (310 for 31 days).
- Moderate news-report length with charts/photos. Preserve extractable Markdown image references/captions; no OCR, image hosting, authenticated-page access or new domain allowance in phase 1. Extraction fidelity remains to be tested.
- Target incremental payment: USD 0. No USD100 allowance, paid fallback or always-on instance approved.
- User confirms Chrome sign-in completed and this project has no active billing account linked. This is user-confirmed, not an independent console inspection.

## Illustrative compute envelope — not a quote or measurement

For comparison only, assume total MCP + Reader allocation 2 vCPU / 4 GiB, and 90 billable seconds per article including an assumed startup/shutdown allowance. This is not a chosen runtime size or evidence that Reader fits it. Additional discovery, OAuth, failure and rejected requests are outside this illustration.

| Articles/month | vCPU-seconds | GiB-seconds |
|---|---:|---:|
| 90 | 16,200 | 32,400 |
| 120 | 21,600 | 43,200 |
| 300 | 54,000 | 108,000 |
| 310 | 55,800 | 111,600 |

Request-based free allowance is 180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million requests, applied by billing account at us-central1 active pricing. Thus this hypothetical compute envelope is below the full allowance, not proof of remaining entitlement or a zero bill. Regional rates and other projects' use matter. Outbound internet traffic, image storage, builds and authentication still need separate assessment. The listed internet egress free allowance is restricted to within North America; do not assume all cross-region internet traffic is free. [Google Cloud Run pricing](https://cloud.google.com/run/pricing), checked 2026-09-12.

Image references avoid storing/serving photo binaries from the MCP service, but Reader's browser may still load images and other resources. Article count alone cannot bound transferred bytes. Do not deploy until all cost rows, including registry retention, have evidence.

## Verified locally

13 tests pass with `.venv/bin/python -m unittest -q`: original URL/Reader cases, no disk archive, admission-time private DNS rejection, unsafe returned URL, access-restriction response, worker timeout/kill, busy rejection, token claim checks, anonymous HTTP rejection, protected-resource discovery and authenticated stateless initialize/tools listing. The stdio smoke check is separate and does not read a live article unless explicitly requested.

The adapter uses public verification keys and owner subject/scope checks. A configured issuer, OAuth discovery/PKCE and actual ChatGPT/Codex sign-in are NOT yet tested. Admission DNS checks do NOT cover the browser's final connections, redirects or subresources. Local tests must not be represented as production security acceptance.

## Deployment gates still open

1. Access: cloud console navigation timed out and the resulting DOM contained no usable project UI. This is not evidence that the project is invalid, lacks billing, or lacks permission. No cloud resource was created. No usable local gcloud was found in earlier environment checks.
2. Billing: blocked pending user decision. User confirms no active billing account is linked. Cloud Run deployment and the Google Cloud Free Tier require billing enabled; free allowances are not a no-billing-account hosting plan. Do not link/create a billing account or accept terms without authorization. If the user permits billing linkage, still inspect shared allowances and all cost gates before deployment. [Google Cloud Free Program](https://docs.cloud.google.com/free/docs/free-cloud-features), [Cloud Run deployment quickstart](https://docs.cloud.google.com/shell/docs/deploy-cloud-run-app), checked 2026-09-12.
3. OAuth: choose a compatible no-extra-charge established issuer and complete real client authorization. Token-verifier scaffolding does not supply the issuer.
4. Reader: pin upstream version/license/build, enforce actual browser network and metadata isolation, verify no plaintext/body logging or persistence; leave independent local Jina untouched.
5. Bounds: durable request quota across cold starts, upstream cancellation/deadline, minimum viable resources and startup measurements. Max instances is not a billing hard cap.
6. Costs: registry/image retention, build, network, logs, secrets/auth and quota storage all need a verified free path before deployment. Stop and request approval for any expected positive cost.
7. Acceptance: cloud probe, controlled article checks, real client authentication, cold start, two-device test and rollback. The current private plugin connection is unchanged.

## Historical v2 user preparation (superseded)

Sign-in and billing-status confirmation are complete per the user. Next decision: permit linking an existing active billing account (not approval of paid resource usage), or require a no-billing-account alternative, which needs a revised architecture assessment. No linkage or new account has been performed. Do not send passwords, API keys or payment-card details. Remaining engineering and cost gates stay our responsibility.
