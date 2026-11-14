# Promise Keeper — Milestone 1 architecture

Contract version: `1`. Proposed MVP baseline; decisions awaiting team agreement are in INTEGRATION.md. No application implementation is included. No shared coding-rules file was present in the available repository; apply it when supplied. Existing README changes belong to their author.

## System and ownership

A browser frontend calls one backend over HTTPS. The backend owns authentication, authorization, validation, PostgreSQL persistence, private evidence storage and an in-process AI adapter. The adapter calls one configured AI provider. No separate AI service, queue, scheduler or microservices are required for the 24-hour MVP.

| Developer | Owns | Integration responsibility |
|---|---|---|
| 1: Frontend | `frontend/` | Case list/detail, upload, editable extraction review, revision confirmation, resolution, complaint preview |
| 2: Backend | `backend/` except `backend/ai/` | API, auth, migrations, transactions, private file access, adapter invocation |
| 3: AI | `backend/ai/` | Extraction, revision suggestions, complaint drafting; no database access |
| 4: Architect/integration | `docs/`, `tests/`, `scripts/`, individually approved root config | Contract consistency, synthetic fixtures, integration checks |

Backend developer must exclude `backend/ai/` from edits. Agree ownership before editing shared manifests or root config. Roles are assignments to confirm, not claims about existing code.

## Request and data flow

1. Frontend sends an authenticated case create request and receives a stable case UUID.
2. Frontend uploads one evidence file. Backend verifies ownership and bytes, stores the immutable original privately, then records its evidence UUID and content hash. File write/DB failures clean up orphaned data.
3. Backend extracts readable text (UTF-8 text or text-layer PDF in MVP), calls the AI adapter with server-selected evidence IDs and existing commitments, validates its output and stores an extraction draft. Scanned PDFs/images needing OCR are outside MVP.
4. Frontend displays proposed values beside original evidence and source quotes. User edits values and explicitly confirms each candidate as new or a revision. AI never creates or changes a commitment directly.
5. Backend validates review data and atomically saves the reviewed commitment, its evidence links, and draft review state. A revision inserts a new row and marks the prior row superseded; original rows and evidence are retained.
6. Backend derives overdue status on reads using UTC time. User can explicitly resolve a case. Complaint generation returns a preview; user copies it. MVP does not send complaints or notifications.

## Data relationships and invariants

All entity IDs and owner IDs are opaque server-generated UUIDs; API examples use UUIDs. `cases.owner_id` comes only from authenticated identity. Every child lookup enforces case ownership. Never accept owner IDs or storage paths from the browser or model.

| Table | Fields / relationships |
|---|---|
| cases | `id`, `owner_id`, `title`, `merchant_name`, `status` (`open`/`resolved` persisted), `version`, `resolution_note`, `resolved_at`, `created_at` |
| evidence | `id`, `case_id` FK, `filename`, `media_type`, `size_bytes`, `sha256`, private `storage_key`, `created_at` |
| extractions | `id`, `case_id` FK, `evidence_ids`, validated `candidates`, `status`, `reviewed_commitment_ids`, `created_at` |
| commitments | `id`, `case_id` FK, `extraction_id` FK, `candidate_id`, `kind`, `description`, `amount_minor`, `currency`, `due_at`, `status`, `supersedes_id` nullable self FK, `reviewed_at`, `created_at` |
| commitment_evidence | `commitment_id` FK + `evidence_id` FK composite primary key, nullable `source_quote` |

A case has many evidence records, extraction drafts and commitments. A commitment links to one or more original evidence records. All links must belong to the same case; enforce in database constraints or transaction validation. Evidence is immutable; no deletion endpoints in MVP. The API exposes an authenticated download path, never `storage_key`.

A revision must reference a currently active commitment in the same case. Prevent branching with a unique non-null `supersedes_id`. A revision keeps its predecessor and original evidence links intact and includes both old and new supporting evidence. Review is transactional; exactly one commitment per `(extraction_id, candidate_id)`. Reviewed drafts cannot be reused.

Case `version` starts at 1 and increments on every successful case mutation, including upload, extraction creation, review and resolution. All mutations on existing cases require `expected_version`. On stale versions return 409 without side effects. Resolve requires at least one active commitment; mark all active commitments fulfilled, preserve superseded rows, and record the user's note and timestamp. No reopening in MVP.

Effective case status: resolved takes precedence; otherwise overdue if any active commitment has non-null `due_at < now`; otherwise open. Equality at the deadline is not overdue. Missing dates never imply overdue. No database cron required.

## Deployment strategy

Develop independently against these fixtures and `/api/v1`. Use one shared staging deployment only after contract agreement. Deploy a frontend static build and a single backend process, managed PostgreSQL, and a private persistent volume (MVP) or private S3-compatible bucket. The AI adapter runs inside the backend. Run migrations once before backend rollout. Local disks must be persistent across redeploys; ephemeral containers require object storage.

Prefer same-origin frontend and `/api` reverse proxy with secure HttpOnly session cookies. Backend developer supplies existing/session identity integration; no public anonymous upload or shared hardcoded user in staging. For cross-origin development allow only the configured frontend origin, send credentials and validate CSRF on mutations. Auth and CSRF failures use the API error format. Terminate TLS, back up database and private files, never commit secrets, and avoid logging evidence text or provider payloads. Provider receives only evidence needed for the current request. No public bucket, static upload directory or permanent public URL.
