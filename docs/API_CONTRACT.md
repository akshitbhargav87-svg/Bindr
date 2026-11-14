# Promise Keeper — API contract v1

Base: `/api/v1`. UTF-8 JSON except uploads/downloads. All routes require an authenticated session and per-case authorization. Unknown or inaccessible IDs return 404. Session setup is an integration dependency owned by backend; identity is not a client-supplied field. Proposed transport: opaque `pk_session` HttpOnly cookie (Secure in HTTPS deployments, SameSite=Lax). Host login/bootstrap supplies a per-session CSRF token in readable `pk_csrf` cookie; frontend echoes it as `X-CSRF-Token` on every POST. Backend verifies token against session and Origin. Use `credentials: "include"` for all browser requests. Login/bootstrap routes are outside the domain API and must be agreed with the backend owner before integration.

## Shared types

Object keys are snake_case. Unknown request keys are rejected (422). IDs are UUID strings. Times are RFC3339 UTC strings ending `Z`. Money uses integer minor units, never floats. Nullable fields must appear explicitly as `null` in complete objects. No undefined/empty-string substitutes. Arrays are always arrays.

| Enum | Values |
|---|---|
| CaseStatus (response) | `open`, `overdue`, `resolved` |
| CommitmentStatus | `active`, `superseded`, `fulfilled` |
| CommitmentKind | `refund`, `replacement`, `service`, `other` |
| ExtractionStatus | `pending_review`, `reviewed`, `rejected` |
| ReviewAction | `new`, `revision` |
| RevisionRelation (AI only) | `new`, `revision`, `uncertain` |

`Terms` = `{ "kind":"refund", "description":"Refund order DEMO-42", "amount_minor":499900, "currency":"INR", "due_at":"2026-11-18T18:29:59Z" }`.
All five keys required. Description 1–2000 trimmed characters. Amount is null or integer 0–9007199254740991; currency null or uppercase ISO 4217 code. Amount/currency are either both null or both populated. A reviewed refund requires both populated. Due date may be null. UI requires user confirmation of ambiguous time zones/dates before setting a timestamp.

Canonical response objects (every listed key is present):

```json
{
  "case": {"id":"11111111-1111-4111-8111-111111111111","title":"Refund for DEMO-42","merchant_name":"Demo Shop","status":"open","version":1,"resolution_note":null,"resolved_at":null,"created_at":"2026-11-14T09:00:00Z"},
  "evidence": {"id":"22222222-2222-4222-8222-222222222222","case_id":"11111111-1111-4111-8111-111111111111","filename":"refund.txt","media_type":"text/plain","size_bytes":120,"sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","created_at":"2026-11-14T09:01:00Z","download_path":"/api/v1/cases/11111111-1111-4111-8111-111111111111/evidence/22222222-2222-4222-8222-222222222222/content"},
  "commitment": {"id":"33333333-3333-4333-8333-333333333333","case_id":"11111111-1111-4111-8111-111111111111","extraction_id":"44444444-4444-4444-8444-444444444444","candidate_id":"c1","kind":"refund","description":"Refund order DEMO-42","amount_minor":499900,"currency":"INR","due_at":"2026-11-18T18:29:59Z","status":"active","supersedes_id":null,"evidence_ids":["22222222-2222-4222-8222-222222222222"],"reviewed_at":"2026-11-14T09:03:00Z","created_at":"2026-11-14T09:03:00Z"}
}
```

Extraction object = `{id, case_id, evidence_ids, status, candidates, reviewed_commitment_ids, created_at}`. `candidates` has exactly the AI_CONTRACT extractor candidate shape; `reviewed_commitment_ids` is empty until reviewed. IDs and time are backend supplied.

## Routes and exact payloads

Placeholders `{case_id}`, `{evidence_id}`, `{extraction_id}` are UUIDs. The names `Case`, `Evidence`, `Commitment`, `Extraction`, `Terms` below denote the exact shapes above, not literal JSON strings. No additional wrappers beyond those shown.

| Method and path | Request | Success response |
|---|---|---|
| POST `/cases` | `{"title":"Refund for DEMO-42","merchant_name":"Demo Shop"}` | 201 `{"case":Case}` |
| GET `/cases` | No body, no query parameters in MVP | 200 `{"cases":[Case]}` sorted created_at descending, then id ascending |
| GET `/cases/{case_id}` | No body | 200 `{"case":Case,"evidence":[Evidence],"commitments":[Commitment],"extractions":[Extraction]}` |
| POST `/cases/{case_id}/evidence` | Multipart described below | 201 `{"evidence":Evidence,"case_version":2}` |
| GET `/cases/{case_id}/evidence/{evidence_id}/content` | No body | 200 raw bytes, original MIME type, safe attachment filename, `Cache-Control: private, no-store`, `X-Content-Type-Options: nosniff` |
| POST `/cases/{case_id}/extractions` | `{"evidence_ids":["22222222-2222-4222-8222-222222222222"],"expected_version":2}` | 201 `{"extraction":Extraction,"case_version":3}` |
| POST `/cases/{case_id}/extractions/{extraction_id}/review` | Review payload below | 200 `{"extraction":Extraction,"commitments":[Commitment],"case_version":4}` (created commitments only) |
| POST `/cases/{case_id}/resolve` | `{"expected_version":4,"resolution_note":"Refund received in full"}` | 200 `{"case":Case}` |
| POST `/cases/{case_id}/complaint-draft` | `{"expected_version":4,"requested_remedy":"Please pay the promised refund"}` | 200 `{"draft":{"subject":"Refund request DEMO-42","body":"...","evidence_ids":["22222222-2222-4222-8222-222222222222"]},"case_version":4}` |

Create title: 1–200 trimmed characters; merchant_name: 1–200. Resolution note and requested remedy: 1–2000. Reads use stable created_at ascending then id ascending for child arrays. List is unpaginated for the small MVP dataset; pagination is deferred. Resolved cases permit reads only; other requests return 409 CASE_RESOLVED.

Extraction accepts 1–10 unique evidence IDs from that case, processes synchronously and returns a pending_review draft; no commitments are saved. No readable text returns 422 UNREADABLE_EVIDENCE. Empty candidates are allowed and may be rejected. Provider timeout/malformed output saves no draft and returns a provider error.

### Review

```json
{
  "expected_version":3,
  "decision":"approve",
  "items":[{
    "candidate_id":"c1",
    "action":"new",
    "supersedes_id":null,
    "terms":{"kind":"refund","description":"Refund order DEMO-42","amount_minor":499900,"currency":"INR","due_at":"2026-11-18T18:29:59Z"},
    "evidence_ids":["22222222-2222-4222-8222-222222222222"]
  }]
}
```

Decision is `approve` or `reject`. Reject requires `items:[]` and marks draft rejected. Approve requires 1–10 items with distinct candidate IDs present in that draft; omitted candidates are discarded when the draft closes. `new` requires null supersedes_id. `revision` requires an active predecessor UUID and includes its original evidence IDs plus at least one evidence ID from this extraction. Every item needs at least one extraction evidence ID; other evidence must be on this case. Backend copies matching source quotes from validated draft sources, or null for user-added evidence; client cannot invent source quotes. User edits are authoritative reviewed terms. Persist `reviewed_at` from server time. `reviewed_commitment_ids` contains returned IDs in review-item order. Whole request succeeds or fails together. Reject response uses `commitments:[]`. Duplicate/repeated review returns 409 DRAFT_CLOSED, never duplicate rows.

### Upload conventions

`multipart/form-data`: exactly one `file` part and one `expected_version` decimal integer string. Client sets the multipart boundary automatically. Maximum file size 10 MiB (10,485,760 bytes). Accept `text/plain` UTF-8 and `application/pdf` with readable text layer. Verify content as well as declared type; reject disguised files. Zero bytes/invalid encoding: 422; unsupported content: 415; excess size: 413. Server chooses random storage keys, computes lowercase SHA-256, strips path components and controls from display filename, and streams downloads only after authorization. Never execute/render original HTML, expose local paths, or return provider-accessible public file URLs. Each upload gets a new evidence ID even for identical bytes. No deduplication/retry guarantee; refresh detail before retrying an uncertain mutation.

## Errors and concurrency

Every non-success JSON response uses exactly:

```json
{"error":{"code":"VALIDATION_ERROR","message":"Invalid request","details":[{"field":"items[0].terms.amount_minor","message":"Must be a nonnegative integer"}],"request_id":"55555555-5555-4555-8555-555555555555"}}
```

`details` is an array (empty for general errors), all fields strings. No stack traces, evidence text, secrets or provider errors in messages. Malformed JSON = 400 INVALID_JSON; 401 UNAUTHENTICATED; 403 CSRF_FAILED; 404 NOT_FOUND; 409 VERSION_CONFLICT / DRAFT_CLOSED / CASE_RESOLVED / INVALID_REVISION / NO_ACTIVE_COMMITMENT; 413 FILE_TOO_LARGE; 415 UNSUPPORTED_MEDIA_TYPE; 422 VALIDATION_ERROR / UNREADABLE_EVIDENCE; 502 AI_INVALID_OUTPUT; 503 AI_UNAVAILABLE; 504 AI_TIMEOUT; 500 INTERNAL_ERROR. Other HTTP methods = 405 METHOD_NOT_ALLOWED in the same envelope. Versions are positive integers. On 409 refetch detail and ask user to review fresh state. Backend must check the version again inside the final transaction after slow AI/storage work. Failed operations do not increment version. Complaint preview is not persisted and does not increment version, but must reject a stale snapshot after generation. Never automatically retry POST requests in the frontend.
