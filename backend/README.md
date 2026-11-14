# Bindr Backend Service

FastAPI-powered backend service providing case tracking, cryptographic session authentication, private evidence storage, and AI-driven promise extraction.

---

## 1. Prerequisites

* **Python:** 3.12 or higher.
* **Virtual Environment:** Recommended (`venv` or `conda`).

---

## 2. Installation

1. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   ```

2. Install core backend dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. (Optional) Install OCR and AI extraction dependencies for local document processing:
   ```bash
   pip install -r backend/app/ai/requirements-ai.txt
   ```

---

## 3. Environment Configuration

The backend operates with sensible defaults for local development. You can customize variables in your shell environment or a `.env` file:

```bash
# Database (defaults to local SQLite database)
DATABASE_URL=sqlite:///./promise_keeper.db

# Environment mode ('development', 'staging', or 'production')
ENVIRONMENT=development

# Session Signing Secret (required for production; defaults to dev key in development)
AUTH_SECRET=bindr_dev_secret_hmac_key_min_32_characters_long_2026

# AI Promise Extraction Provider ('mock' for deterministic tests, 'meta' for live API)
AI_PROVIDER=mock

# Live Meta Model API (required only if AI_PROVIDER=meta)
# MODEL_API_KEY=your_meta_api_key_here
# META_MODEL=muse-spark-1.3
# META_BASE_URL=https://api.meta.ai/v1

# Evidence Storage ('local' or 'gcs')
EVIDENCE_STORAGE_BACKEND=local
EVIDENCE_STORAGE_DIR=./storage/evidence
```

For full reference, see `docs/ENVIRONMENT.md`.

---

## 4. Starting the FastAPI Server

Launch the development server with live reload:

```bash
uvicorn backend.app.main:app --reload --port 8000
```

Once running:
* **Interactive API Docs (Swagger):** `http://localhost:8000/docs`
* **Alternative API Docs (ReDoc):** `http://localhost:8000/redoc`

---

## 5. Health & Readiness Check

Verify service health via the unauthenticated readiness endpoint:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "Bindr"
}
```

The health check confirms that database connectivity and required backend components are functioning properly. The endpoint is also available at `/api/v1/health`.

---

## 6. Running Tests

Run the full integration regression test suite:

```bash
pytest tests/regression
```

Run targeted backend model and service tests:

```bash
python -m unittest discover backend/app/tests
```

---

## 7. Key Architecture & Endpoints

* **Authentication & CSRF Bootstrap:**
  * `POST /api/v1/auth/bootstrap` — Generates signed session cookie and returns matching CSRF token.
* **Cases Management:**
  * `POST /api/v1/cases` — Create a case.
  * `GET /api/v1/cases` — List cases owned by current session.
  * `GET /api/v1/cases/{case_id}` — Get case details, timeline, commitments, and extractions.
  * `POST /api/v1/cases/{case_id}/resolve` — Mark case resolved with optimistic concurrency check.
* **Evidence Handling:**
  * `POST /api/v1/cases/{case_id}/evidence` — Upload evidence (PNG, JPEG, PDF, text/plain, max 10 MiB).
  * `GET /api/v1/cases/{case_id}/evidence/{evidence_id}/content` — Authenticated, private evidence download with `Cache-Control: private, no-store`.
* **AI Extraction & Review Workflow:**
  * `POST /api/v1/cases/{case_id}/extractions/draft` — Trigger OCR and AI extraction pipeline.
  * `POST /api/v1/cases/{case_id}/extractions/{extraction_id}/review` — Human review and confirmation of promise candidates into active commitments.
