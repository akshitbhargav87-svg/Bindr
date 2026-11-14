# Combined release audit — 14 November 2026

> This records the original integrated release. Hosting now targets Google Cloud; see the [migration audit](GOOGLE_CLOUD_MIGRATION.md) and [deployment guide](DEPLOYMENT.md). Historical Render evidence below is preserved. The subsequent Google deployment and real-provider checks are recorded in [live acceptance](LIVE_ACCEPTANCE.md).

## Result

The assembled app passes local frontend, backend, AI/OCR and integration checks. The actual typed frontend adapter also completes the real FastAPI lifecycle. **Public deployment, PostgreSQL on Render, and the live Meta provider still need verification.** Local provider tests deliberately use an explicitly selected offline extractor or controlled provider responses; they are not evidence of paid live inference.

## Branch integration

All five original branch heads were inspected and their source combined on `release/hackathon-live`:

| Branch | Audited original head | Contribution |
|---|---|---|
| main | 870f244 | Project foundation |
| feature/frontend | 5692da9 | Frontend phases 1–7 |
| feature/milestone-1-backend | 42a50f9 | API, storage, auth and review |
| feature/milestone-1-promise-extraction | 6cd0476 | Provider schema, deadlines and document processing |
| feature/integration | cc27ec9 | Contracts and regression evidence |

Merge commits preserve original authors. AI add/add conflicts were resolved using the latest AI-owner branch, followed by independent backend, frontend and AI audits of the combined source. Feature branches remain intact. GitHub contributor display also depends on commit email association and may update asynchronously.

## Material corrections

- Added missing resolve and complaint routes; complaint text uses reviewed facts and does not send anything.
- Replaced publicly selected user identity with random browser-owned workspaces; blocked legacy manual commitment bypass routes in production.
- Added production cookie settings, automatic frontend bootstrap, CSRF recovery and production-origin handling.
- Required current versions and atomic version claims around uploads/extraction/review/resolution. No automatic POST retries.
- Enforced strict AI schema, exact quotes and evidence membership; removed fabricated fallback citations and provider-response logging.
- Preserved original/revised sources, currency, nullable money and uncertain dates. Non-INR values no longer silently become INR; mixed currencies are not added together.
- Kept unfinished records reachable after refresh, with pending-review recovery.
- Enabled PNG/JPEG OCR, cached/serialized model execution, bounded document size/pages/pixels, private file permissions and modest public demo limits.
- Added PostgreSQL driver/64-bit money support, safer legacy SQLite upgrades, same-origin production frontend serving, real database readiness and repeatable deployment configuration.

## Verification

| Check | Result |
|---|---|
| Native backend + AI tests | 123 passed |
| Original integration regression suite with valid signed test sessions and cached OCR assets | 28 passed; no skips |
| Frontend checks | 59 passed |
| TypeScript and connected production build | Passed |
| Actual typed frontend HTTP adapter against real FastAPI/SQLite/private storage | Passed: session → create → upload → extract → approve → revision → complaint → exact original bytes → stale-write rejection → resolve |
| Browser smoke against the connected app | Passed: fresh session, paste, extraction, explicit confirmation, case history and page-refresh persistence |
| Render Blueprint JSON schema | Passed |
| Whitespace/conflict checks | Passed |

Local runtime was Python 3.14 / Node 22. The deployment/CI target is Python 3.12 / Node 22 with pinned runtime requirements. GitHub CI rechecks the target runtime and complete workflow. Non-failing dependency deprecation warnings remain. No local Docker daemon or PostgreSQL server was available, so container startup and production database behavior are not claimed verified here.

OCR initialization peaked around **529 MiB RSS** locally with mobile models, exceeding the 512 MB compute plan before allowing for the rest of the app. The Blueprint therefore uses 2 GB, one process, and a private disk. Model files are prepared during the image build rather than downloaded on the first user's screenshot.

## Remaining acceptance gates

1. Render image build, database provisioning and HTTPS health must succeed.
2. Set the real MODEL_API_KEY and confirm the model/base URL; test actual extraction with synthetic evidence.
3. Repeat the adapter/browser flow against the deployed HTTPS URL, including private-download authorization and records/files across a redeploy.
4. Add the verified live URL to the README. Keep demo-only features clearly distinguished.

The historical [integration audit](../tests/regression/RESULTS.md) records older separate snapshots and remains preserved as evidence; this document describes the combined release corrections.
