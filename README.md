# Bindr

**A promise. A deadline. A clear record.**

[Deployment URL](https://bindr-tor2633xpq-el.a.run.app) · [Editable flowcharts](docs/diagrams/README.md) · [Integration status](docs/intelligence/COMBINED_MVP_STATUS.md)

Companies promise refunds, replacements and service fixes across messages and documents. When dates change, the proof gets scattered. Bindr keeps the original communication, reviewed promises, revisions and actual outcomes together.

> **Current status — 15 November 2026:** implementation and integration are in progress. The v2 backend, AI adapter and separate React tools have been connected locally. A Google Cloud cutover was recorded, followed by a browser-request fix and restoration of the original UI in source. The restoration's live deployment and the requested traffic rollback have not been confirmed. The full roadmap, real-model acceptance and live account/privacy checks are **not complete**. Earlier release reports describe their own revisions, not acceptance of this branch.

## The journey

1. Sign in with Google or a verified email account; optional authenticator MFA is implemented through Firebase/Identity Platform.
2. Paste the original company message or attach supported evidence. Preserve original bytes and review the source communication date; it must not be guessed from upload time.
3. Inspect AI-suggested terms beside their exact quotations. Screenshots use real OCR. Suggestions remain unconfirmed until a person reviews them.
4. Confirm the promises to track, their amounts/currencies and any known deadlines. Vague dates and unknown conditions stay unresolved.
5. Add later communications and explicitly review revisions. Earlier terms and original sources remain available.
6. Follow through with an actual outcome. The v2 ledger supports partial receipts and per-obligation balances; a company's claim that it processed a payment does not prove receipt.
7. Use source-cited case answers and private evidence exports in the separate v2 tools. Review follow-up wording yourself; Bindr does not automatically send or file complaints.

**Example:** a fictional ₹4,999 refund, followed by a ₹1,000 actual receipt, leaves ₹3,999 outstanding. This illustrates the v2 ledger; it is not a verified live recovery or a claim about the main v1 screen's totals.

![Bindr customer journey](docs/images/customer-journey.png)

*Dashed boxes identify v2 capabilities whose integration through the original main screens is still pending. [Open the editable Excalidraw source](docs/diagrams/01-bindr-customer-journey.excalidraw).*

## What is implemented, and where

| Area | Current implementation and boundary |
|---|---|
| Original product UI | The original overview, case list, upload/paste, source-side review and case-detail components are restored in source. Subsequent polish adds the corrected wordmark, aligned labels, consistent settings typography, a shared date-only calendar and reduced-motion-aware feedback. Their main data path remains `/api/v1`. The integration prototypes no longer replace these default screens. |
| Accounts | Firebase verified identity, Google/email sign-in, reset and optional MFA; revocable SQL sessions, HttpOnly cookies and CSRF/account checks. Real reset/reuse/MFA, cross-device recovery and isolation acceptance remain open. |
| AI and review | Explicit v1/v2 adapters; bounded all-candidate structured extraction, quote/schema/money validation, conditional/revision relationships and typed failures. The real Meta key reference exists in the cloud configuration. The ten canonical inputs plus dated 1B have not passed fresh real-Meta acceptance. No silent model-error-to-mock fallback. |
| OCR and imports | PNG/JPEG RapidOCR, plain text and text-layer PDF processing. Mixed/scanned-PDF, EML/MIME, MSG and audio/segment adapters have partial independent implementations; their dispatch, optional dependencies, transcription provider and multilingual quality are not fully accepted. |
| V2 platform | Versioned multi-promise review, manual attestation, deterministic deadline proposals, append-only outcomes/corrections, partial/full receipts, revision history, lifecycle and requested deletion services. These are separate from legacy v1 facts. |
| Capture and recovery | Account-bound in-memory recovery, identity-epoch protection, stable operation keys and original-byte fingerprints; opt-in account draft autosave. Browser/process loss and cross-device acceptance are not implied by local fixtures. |
| Ask a case | Bounded authorized source snapshots, exact citations or abstention. The pure answer engine does not gain tools, browse another case or perform writes. |
| Private exports | V2 selected PDF/data/original ZIP snapshots, SHA-256 manifests, private authenticated download and optional offline verification. Jobs queue for the maintenance worker; live cloud artifact/expiry acceptance remains open. |
| Maintenance | Cloud Run Job + durable SQL leases + authenticated minute Scheduler were configured during rollout. The scheduled worker is restricted to exports, expiry and requested case/account deletion; unattended execution has not been established by the supplied screenshots. |
| Optional expansion | PWA sharing and Chrome-extension sources exist. Gmail/Resend/WhatsApp, reviewed correspondence, push/email reminders and external timestamps require provider configuration/integration and acceptance. They are not presented as enabled features. Public aggregates remain disabled. |

### UI/API boundary

The normal routes `/app`, `/app/cases`, `/app/upload`, `/app/review` and `/app/cases/:caseId` use the original designed components. The main capture/review flow still uses its existing v1 adapter. The v2 interfaces remain separately accessible at:

- `/app/tools/workspace-v2`
- `/app/tools/capture-v2`
- `/app/cases/:caseId/workflow`

`/app/capture-v2` now opens the original capture screen. `VITE_ENABLE_V2_CAPTURE=true` enables relevant data/tool features at build time; it no longer swaps the normal overview/capture screens for the integration prototypes. Legacy amounts and receipts are not invented or silently merged into v2 totals. Completing that connection **must preserve the original UI**. See [the restoration record](docs/intelligence/ORIGINAL_UI_RESTORATION.md) and [subsequent UI polish](docs/intelligence/UI_POLISH_2026-11-15.md). A selected calendar day remains `YYYY-MM-DD`; the picker itself does not invent a deadline time.

## Architecture

![Bindr technical architecture](docs/images/technical-architecture.png)

*[Editable technical diagram](docs/diagrams/02-bindr-technical-architecture.excalidraw) · [Two-page PDF](docs/diagrams/Bindr-flowcharts-16x9.pdf). The diagram describes current source and configured infrastructure, not full production acceptance.*

- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, Lucide and the existing Bindr design components.
- **API/data:** Python 3.12 container, FastAPI, Pydantic, SQLAlchemy, PostgreSQL in Cloud SQL. SQLite is for local development.
- **Documents/AI:** RapidOCR/ONNX and PyMuPDF; the configured Meta Model API adapter supplies proposals. Deadlines and money are validated outside the model. Case answers are grounded in the authorized source snapshot.
- **Identity:** Firebase/Google Identity Platform plus revocable Bindr SQL sessions; provider passwords and second factors remain with Google.
- **Cloud:** Cloud Run serves frontend and API from one HTTPS origin. Private Cloud Storage holds originals/artifacts. Secret Manager and service IAM hold signing/database/model credential references. Cloud Build produces Docker images from the release source.
- **Jobs:** SQL leases and bounded worker batches, invoked by Cloud Run Jobs and OAuth-authenticated Cloud Scheduler. External notifications and Gmail sending remain disabled; maintenance-only scheduling does not activate them.

Ownership, strict request schemas, stable operation replay, stale-version conflicts and private downloads are server responsibilities. AI proposes; only reviewed transactions create facts. Original evidence is immutable while retained; explicit deletion has its own cleanup and backup-retention boundaries. Digests detect changes, not truth, authorship or legal acceptance.

## Run locally

Requires Python 3.12+ and Node.js 22. From the repository root, in Bash:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-runtime.txt
cd frontend
npm ci
VITE_USE_MOCK=false VITE_ENABLE_V2_CAPTURE=true VITE_API_URL=/api/v1 npm run build
cd ..
ENVIRONMENT=development AUTH_PROVIDER=anonymous AI_PROVIDER=mock \
  uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. This starts the real local API/storage with an explicitly selected offline v1 extractor; it does not establish live AI or supply a structured v2 model. The v2 structured provider fails explicitly when not configured. Deployed anonymous authentication is forbidden.

For real inference, configure `AI_PROVIDER=meta`, `MODEL_API_KEY`, the provider-confirmed `META_MODEL` and `META_BASE_URL` in the **server environment before starting it**. Existing cloud secret references can supply the key without a local copy. A bare `.env` file is not loaded automatically by the current settings class. Never put secrets in Git, `VITE_` variables or chat. Firebase local configuration follows [the account guide](docs/AUTHENTICATION.md).

## Update the existing Google Cloud deployment

Use [platform operations](docs/platform/OPERATIONS.md), [the v2 update record](docs/intelligence/CLOUD_V2_UPDATE.md) and [the original-UI restoration record](docs/intelligence/ORIGINAL_UI_RESTORATION.md). Git pushes alone do not deploy.

- `scripts/release_existing_google_cloud.py` prepares a full existing-service rollout: build, confirmed SQL backup, explicit additive schema migration, maintenance-only schedule, named-revision readiness/config checks and traffic cutover. **Schema target: 11.** Startup checks the deployed schema; it does not silently upgrade production.
- `scripts/release_frontend_hotfix.py` + `Dockerfile.frontend-hotfix` replace frontend assets over an existing immutable backend image, preserving runtime settings. This path does not rerun migrations or worker provisioning.
- `scripts/migrate_platform.py --check` checks the schema; `--upgrade` explicitly applies the additive migration. Backup restoration has not been rehearsed by the rollout utility.
- `scripts/platform_worker.py --max-jobs 20 --maintenance-only` processes only exports and requested deletion maintenance. External reminders/sends need their own reviewed activation and real delivery evidence.

The last supplied traffic confirmation was **100% to `bindr-v2-6eaebc69-022612`**, image source `6eaebc69b97d`, on 15 November 2026. Later screenshots show the frontend hotfix in the browser, followed by a request to restore the original UI and a traffic rollback command. The exact hotfix revision and execution of that rollback were not supplied; this README does not assert the current live revision. The original-UI restoration is present in this branch's source.

The older `scripts/deploy-google-cloud.sh` is retained for historical setup; do not use it alone for a v2 schema/worker rollout. Render and S3-compatible diagrams in older handoffs are historical; the current implementation uses Google Cloud and includes no S3 storage implementation.

## Verification and remaining work

The combined pre-rollout suite recorded **296 passed, 2 failed, 3 subtests passed**; the preserved integration regressions recorded **28 passed**. Those are historical local results with controlled inference, not a fresh green run of the latest revision. The two recorded failures received source corrections without a rerun at the owner's request. Frontend production builds subsequently passed, but a real-browser fetch binding failure was discovered after rollout and corrected separately. Original QA verdicts remain unchanged.

Still required: connect v2 through the original UI; real Meta canonical-case acceptance; full browser/account/privacy and stale-complaint coverage; connected imports; real worker/artifact/retention behavior; backup restoration and current combined CI. Deferred connectors, audio, public aggregation and timestamps must not be advertised as complete.

Read [combined evidence](docs/intelligence/COMBINED_MVP_STATUS.md), [frontend incident](docs/intelligence/FRONTEND_INCIDENT_2026-11-15.md), [Track A status](docs/IMPLEMENTATION_STATUS_A.md) and [Track B status](docs/IMPLEMENTATION_STATUS_B.md). Older reports/phase handovers are dated snapshots and may be superseded by the integration/incident records.

## Team

- **Akshit Bhargav:** product, integration/release coordination; Track A platform/data/API work.
- **Tushar Aggarwal (`biney25`):** frontend, capture UX and Track B intelligence integration.
- **Lokesh Goel (`lokesh-27-goel`):** original backend contribution.
- **Kunal Gupta:** original AI extraction/document-processing contribution.

Original feature/account histories and author attribution are preserved. The diagrams are editable Excalidraw sources with embedded assets; their [README](docs/diagrams/README.md) records scope, rebuild instructions and logo/font provenance.
