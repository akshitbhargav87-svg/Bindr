# Bindr backend

FastAPI provides browser sessions, owned cases, private evidence, Meta extraction, reviewed promises, revisions and full resolution. Run the commands below from the **repository root**, using Python 3.12+.

The combined branch also includes Firebase account sessions and the separate v2 ledger, extraction/review, outcomes, private exports, requested deletion and durable jobs. The original frontend still uses v1 for its main capture/review flow; v2 tools do not silently reinterpret legacy facts. See [the published v2 packet](../docs/platform/API_V2_PACKET.md), [operations](../docs/platform/OPERATIONS.md) and [current integration status](../docs/intelligence/COMBINED_MVP_STATUS.md). Earlier live acceptance belongs to its recorded image, not this combined source.

## Install and run locally

Bash (macOS/Linux):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-runtime.txt 'pytest>=8,<9'
export AI_PROVIDER=mock
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

PowerShell (Windows):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements-runtime.txt 'pytest>=8,<9'
$env:AI_PROVIDER='mock'
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

The shared pinned runtime includes the document-processing imports needed by the app; core requirements alone are insufficient. Local defaults use SQLite and private files in `storage/evidence`. `mock` is an explicitly selected offline demonstration extractor, not live AI. The backend defaults to `meta` otherwise, and reports missing credentials instead of silently falling back.

Set configuration in the process environment before starting the server. Bash variables must be exported; PowerShell uses `$env:VARIABLE='value'`. Do not assume a root `.env` file loads all backend settings. See the [actual environment reference](../docs/ENVIRONMENT.md). Production requires a random `AUTH_SECRET` and private persistent storage; keep live keys in Secret Manager or the server environment, never in Git or `VITE_` variables.

## Health and browser assets

- `GET /health` runs a real database query and returns `{"status":"healthy","service":"Bindr"}` on success. It does not test the AI provider or bucket access.
- `/healthz` is the local/Render compatibility alias; use `/health` publicly on Cloud Run.
- `/api/health` and `/api/v1/health` are legacy informational routes and do not run the same database check.
- Interactive API documentation is at `http://127.0.0.1:8000/docs`.
- Build the frontend using the [root README](../README.md) for the combined browser app. Without built assets, the homepage returns 503 while API routes remain available.

## Tests

After installing the runtime and pytest, run backend and AI tests from the root:

```bash
python -m pytest backend/app/tests backend/app/ai/tests -q
```

Screenshot checks use real OCR. Prepare public model files once with network access before an offline regression run:

```bash
# Bash; PowerShell equivalent: $env:OCR_MODEL_DIR=(Join-Path $PWD '.ocr-models')
export OCR_MODEL_DIR="$PWD/.ocr-models"
python -c 'from backend.app.ai.document_processor import warm_ocr_models; warm_ocr_models()'
python scripts/run_integration_regressions.py --source . --auth-hook tests/regression/final_acceptance/signed_session.py --ocr-model-dir .ocr-models
```

The regression runner isolates storage/database configuration and supplies a test-only signed-session hook. Use pytest for the function-based backend tests; unittest discovery alone does not run them. Tests use synthetic evidence and offline/controlled provider responses; the [live acceptance report](../docs/LIVE_ACCEPTANCE.md) separately records real Meta and Google Cloud checks.

## Main API routes

| Purpose | Route |
|---|---|
| Create/inspect browser session | `POST /api/v1/auth/session`, `GET /api/v1/auth/session` |
| Create/list cases | `POST /api/v1/cases`, `GET /api/v1/cases` |
| Read case and related records | `GET /api/v1/cases/{case_id}` |
| Upload original evidence | `POST /api/v1/cases/{case_id}/evidence` |
| Private original download | `GET /api/v1/cases/{case_id}/evidence/{evidence_id}/content` |
| Extract pending suggestions | `POST /api/v1/cases/{case_id}/extractions` |
| Explicitly approve/reject suggestions | `POST /api/v1/cases/{case_id}/extractions/{extraction_id}/review` |
| Preview a factual complaint | `POST /api/v1/cases/{case_id}/complaint-draft` |
| Confirm full resolution | `POST /api/v1/cases/{case_id}/resolve` |

State-changing cookie requests require the matching CSRF token, permitted origin and expected account; case writes require the current case version. V2 mutations additionally require stable account/operation-scoped idempotency keys. Original files stay private, and suggestions do not become commitments before review. V2 partial receipts and privacy/recovery acceptance limits are documented in the [root README](../README.md). Deployed startup checks schema revision 11; migration is an explicit operation. The maintenance worker is separately scheduled and does not enable optional external sends. For the existing Google service, follow the [update instructions](../docs/DEPLOYMENT_GOOGLE_CLOUD.md), preserving the database, bucket and secrets.
