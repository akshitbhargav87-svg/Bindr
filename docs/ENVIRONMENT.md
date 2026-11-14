# Environment configuration — Reference

Documented settings represent the actual configuration contract for the Bindr backend and AI modules. Backend validates required settings at startup and keeps secrets strictly server-side. Do not commit `.env` files or log secret values.

| Variable | Consumer | Required / Example and Meaning |
|---|---|---|
| `DATABASE_URL` | Backend | `sqlite:///./promise_keeper.db` for local development; `postgresql://user:pass@host:5432/dbname` (with TLS) for Cloud Run / Render production deployments. |
| `ENVIRONMENT` | Backend | Application environment: `development` (default), `production`, or `staging`. Deployed environments enforce strict signing secrets and HTTPS-only cookies. |
| `AUTH_SECRET` | Backend | Required HMAC-SHA256 session signing secret. In deployed environments (`production`, `staging`), must be at least 32 characters long; predictable/default keys are strictly forbidden at startup. |
| `SESSION_LIFETIME_SECONDS` | Backend | Session age limit (default: `86400` / 24 hours; deployment script: `2592000` / 30 days). Expiry is derived from the signed issuance timestamp; there is no separate `exp` claim. |
| `CLOCK_SKEW_TOLERANCE_SECONDS` | Backend | Allowable clock skew for session timestamp verification (default: `60` seconds). |
| `CORS_ORIGINS` | Backend | Comma-delimited list of allowed frontend origins (default: `http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173`). Wildcards (`*`) are disallowed when credentials are enabled. |
| `FRONTEND_ORIGIN` | Backend | Explicit frontend origin appended to allowed CORS and CSRF origin check (e.g. `http://localhost:5173` or production domain). |
| `RENDER_EXTERNAL_URL` | Backend | Same-origin external URL automatically populated on Render deployments. |
| `FRONTEND_DIST_DIR` | Backend | Filesystem path to built frontend static assets for single-origin serving (default: `frontend/dist`). |
| `EVIDENCE_STORAGE_BACKEND` | Backend | Evidence storage driver: `local` (default) or `gcs` (production). |
| `EVIDENCE_STORAGE_DIR` | Backend | Absolute filesystem path for local evidence storage (default: `<cwd>/storage/evidence`). Must be private and outside public web roots. |
| `EVIDENCE_GCS_BUCKET` | Backend | Google Cloud Storage bucket name for private evidence storage. Required when `EVIDENCE_STORAGE_BACKEND=gcs`. Accessed via Cloud Run service account identity with uniform bucket access and public access prevention enabled. |
| `AI_PROVIDER` | Backend AI | Promise extraction provider: `meta` (default) or `mock` (offline test/demo extractor). Missing Meta credentials produce an error, without silently switching to mock. |
| `MODEL_API_KEY` | Backend AI | Secret API key for Meta Model API. Required when `AI_PROVIDER=meta`. |
| `META_MODEL` | Backend AI | Model identifier for extraction engine (default: `muse-spark-1.3`). |
| `META_BASE_URL` | Backend AI | Base URL endpoint for Meta Model API (default: `https://api.meta.ai/v1`). |
| `META_TIMEOUT` | Backend AI | Provider request timeout in seconds (provider default: `30`; deployment script: `45`). |
| `OCR_MODEL_DIR` | Backend AI | Optional directory path for prewarmed RapidOCR PP-OCRv4 ONNX model weights. |

## Storage & Security Invariants

* **Private Evidence Access:** All evidence downloads are backend-mediated via `GET /api/v1/cases/{case_id}/evidence/{evidence_id}/content`. Neither public object URLs nor signed URLs are ever generated. Downloads enforce `Cache-Control: private, no-store` and `X-Content-Type-Options: nosniff`.
* **Upload Limits:** The upload size limit is 10 MiB (`MAX_UPLOAD_SIZE_BYTES = 10485760`). Maximum extraction text length is 50,000 characters.
* **Format Validation:** Files are validated using binary magic bytes (PNG, JPEG, PDF, UTF-8 text) to prevent disguised uploads.
* **Integrity & Immutability:** Stored files are written with random UUID keys (`<evidence_id>.bin`) and SHA-256 hashed upon ingestion. Original evidence files are never modified, compressed, or overwritten.
