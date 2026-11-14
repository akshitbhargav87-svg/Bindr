# Integration gaps

Contract snapshot: feature/integration @ 70f2db0, version 1. No endpoints invented.

Phase 3 update: capture, processing, extraction review, explicit confirmation and recovery are implemented. HTTP mutations follow the existing create/upload/extract/review contract; there is no invented manual endpoint. Mock mutations retain originals in memory and support local text extraction, explicit manual entry and duplicate suggestions. Files/records are not persisted across reload. Full case timelines, outcomes and dedicated evidence browsing remain Phase 4. See PHASE-3-HANDOVER.md.

Phase 2: HTTP dashboard/list reads combine the contracted list and bounded detail reads. Rich mock status is computed in the mock adapter; HTTP status stays server-provided with missing dates displayed as Needs a date. No browser-clock overdue/due-today calculation was added. Reference date, server timezone metadata and Due today remain contract gaps.

- **Session bootstrap:** contracts require authenticated cookies + CSRF, while the product prompt requests no auth UI. Backend must supply the session outside the domain API. HTTP adapter carries cookies and echoes CSRF; no credentials are hardcoded.
- **Images/OCR:** backend accepts only text/plain and text-layer PDF, max 10 MiB per file. PNG/JPEG extraction requires backend support; do not present images as accepted in HTTP mode.
- **Communication dates/calendar:** uploads accept only file + expected_version. No occurred_at field or deterministic relative-date calculation response is contracted. Mock-only calendar behavior must not leak into components.
- **Rich status labels:** API case status is open/overdue/resolved. Due today/needs a date needs backend enrichment for production; do not derive authoritative status using a browser clock.
- **Case list summaries:** list returns no commitment amount/deadline; aggregate fields or detail reads will be needed.
- **Manual entry:** review requires an existing extracted candidate; there is no endpoint to persist an independent manual commitment after extraction failure.
- **Manual mock representation:** the local extension stores user-confirmed terms and original evidence without fabricating an AI draft or quotation. Its generated extraction_id has no extraction record; production needs a contracted manual-origin representation before integration.
- **Identity edits:** company/title editing after case creation has no HTTP endpoint. Review edits update mock records only; HTTP review keeps the created identity fixed.
- **Uncertain create result:** no idempotency key or request lookup is contracted. A lost create response blocks automatic retries; backend reconciliation is required. Lost upload responses can be checked against original filename and SHA-256, and a matching upload is reused.
- **Case lifecycle:** no partial outcome, reopen, edit, archive/restore or delete endpoints.
- **Other surfaces:** no duplicate detection, saved drafts, agenda, inbox, settings or notification endpoints.
- **Complaint export:** contract supports preview text only, no PDF/file export or draft persistence. Copy-to-clipboard is the contracted MVP path.

Implemented mock mutations are create, upload, extract, review and explicit manual entry. Resolve and complaint methods still return PHASE_NOT_IMPLEMENTED for their later phases. GAP comments identify unsupported integration boundaries. No backend was changed or verified end to end.
