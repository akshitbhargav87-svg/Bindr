# Minimal integration test plan (implementation deferred)

Milestone 1 supplies a plan and synthetic snapshots, not an application test runner. The four JSON files in fixtures/ use `{scenario, as_of, evidence_text, expected}`. `expected` is exactly the case-detail response shape. Text map keys are evidence UUIDs; fixture filenames/hashes/byte sizes describe those synthetic UTF-8 text values, not actual uploaded files. Seed/driver integration is the backend/integration owners' later responsibility. All data is fictional. Freeze the server clock at as_of; do not compare against wall-clock dates.

Prerequisites: isolated PostgreSQL, private temporary storage, two authenticated users, deterministic AI stub, browser/API client. No real customer evidence or live paid AI. Backend owner supplies reset/seed tooling later.

| Test | Steps and required assertion |
|---|---|
| New refund | Create case, upload new-refund text, stub candidate, fetch detail before approval: no commitments. Edit and approve; compare persisted terms and IDs/links with fixture semantics. |
| Revision | Begin with new-refund state, upload revised text, propose/approve revision. Old row is superseded, new row points to it, both original and new evidence IDs retained; original bytes/hash unchanged. |
| Overdue | At overdue fixture clock, active non-null deadline before now gives overdue; deadline equal to now and null deadline give open; superseded deadlines do not affect status. |
| Resolved | Resolve with note; all active commitments become fulfilled, resolved timestamp recorded, case resolved despite past deadline. Subsequent writes return CASE_RESOLVED. |
| Privacy | User B cannot list/read/change A's case, upload/extract/review/resolve/generate complaint/download evidence. Guessed IDs return 404; unauthenticated calls 401. No storage key or public upload URL in JSON. CSRF failures reject mutations. |
| Upload | Valid text/text PDF works. Reject oversized, empty, spoofed MIME, invalid UTF-8, unreadable PDF and path-bearing filename. Confirm private attachment headers and original bytes. |
| Validation | Reject unknown fields, invalid UUID/date/enums, cross-case references, unpaired money, noninteger amounts and unreviewed incomplete refund. Zero candidates stays draft and can be rejected. |
| Review gate | UI requires explicit confirmation. API review rejects invented candidate IDs and closed drafts; reject saves no commitment. Editing model suggestions stores user values only. |
| Concurrency | Two clients use one version; only one mutation succeeds. Concurrent revisions cannot branch. Duplicate review returns 409; partial multi-item failure rolls back all writes/version changes. Recheck stale version after slow AI. |
| AI failure | Stub malformed JSON, made-up evidence ID, nonmatching quote, ambiguous date, prompt injection, timeout/unavailable. Invalid output creates no draft or commitment; errors use contract envelope without private payloads. |
| Complaint | Uses reviewed facts/current revision, returns evidence IDs and editable plain text; no email/network submission and no DB change. Missing active commitment or stale version rejects. |

Acceptance for implementation: all rows pass, ownership/privacy failures block release, and frontend/backend/AI owners record results against the same contract revision. Static JSON parsing and link/reference checks in Milestone 1 do not establish runtime behavior.
