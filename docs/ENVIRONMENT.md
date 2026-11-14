# Environment configuration — MVP proposal

Documented names are the shared implementation contract. No root configuration file or real credentials are created in Milestone 1. Backend validates required settings at startup and keeps secrets server-side. Do not commit `.env` files or print values.

| Variable | Consumer | Required / example and meaning |
|---|---|---|
| `DATABASE_URL` | Backend | Required; `postgresql://promise:LOCAL_ONLY@localhost:5432/promise_keeper`; use deployment secret with TLS remotely |
| `AI_PROVIDER` | Backend AI | Required; `stub` locally/tests, `openai` proposed production adapter |
| `AI_API_KEY` | Backend AI | Required only for live provider; secret, never frontend-prefixed |
| `AI_MODEL` | Backend AI | Required live-provider model identifier, selected by AI owner; no assumed model default |
| `AI_TIMEOUT_SECONDS` | Backend AI | `45` default; align proxy timeout above it |
| `APP_TIMEZONE` | Backend | `Asia/Kolkata` proposed default for explicitly interpretable evidence; never silently resolve ambiguous dates |
| `EVIDENCE_STORAGE_DRIVER` | Backend | Required: `local` or `s3` |
| `EVIDENCE_LOCAL_DIR` | Backend | Required for local; absolute private persistent directory outside frontend/public/static roots |
| `EVIDENCE_S3_ENDPOINT` | Backend | Optional S3-compatible HTTPS endpoint; absent uses provider default |
| `EVIDENCE_S3_REGION` | Backend | Required for s3 |
| `EVIDENCE_S3_BUCKET` | Backend | Required for s3; private bucket with public access blocked |
| `EVIDENCE_S3_ACCESS_KEY_ID` | Backend | Required for s3 unless workload identity configured; secret |
| `EVIDENCE_S3_SECRET_ACCESS_KEY` | Backend | Same requirement as access key; secret |
| `FRONTEND_API_BASE_URL` | Frontend build | Public setting; `/api/v1` for same origin or `http://localhost:8000/api/v1` for development. Frontend owner maps to framework build configuration without renaming the shared logical setting |
| `FRONTEND_ORIGIN` | Backend | Required origin for CORS/CSRF; e.g. `http://localhost:5173`; no wildcard with cookies |
| `SESSION_SECRET` | Backend | Required secret for signed session, at least 32 random bytes; never use example credentials in staging |

Use backend-mediated evidence downloads even with S3; do not create public object URLs. Upload limit (10 MiB) and extraction text limit (50,000 characters) are fixed contract constants for MVP. Agree session integration, runtime and provider before implementing their setup. Configure test database/storage independently from staging; fixtures contain synthetic content only.
