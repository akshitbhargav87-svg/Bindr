# Integration gaps

Contract snapshot: feature/integration @ 70f2db0, version 1. No endpoints invented.

Phase 4 update: detail, source-linked original/revised timelines, evidence library/downloads and full fulfilment are implemented against the existing contract. Partial/pending outcomes, reopen, archive/restore, deletion, identity correction and claim/decision annotations are local mock extensions. Connected mode disables unsupported management actions and explains note persistence limits. New state and file bytes still reset on reload. Earlier phase notes below are historical where superseded. See PHASE-4-HANDOVER.md.

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
- **Case lifecycle:** no partial outcome, reopen, edit, archive/restore or delete endpoints. Mock partial receipts preserve the reviewed amount/deadline and subtract only confirmed receipts from outstanding totals. Full resolution uses the real /resolve contract. Mock reopening preserves earlier outcome events and explicitly restores the full promise to outstanding. Company/title corrections preserve canonical promise terms; deadline/amount changes go through revision review.
- **Timeline metadata:** communication dates, user check-ins, company-claim labels and revision decision notes have no HTTP fields. HTTP keeps the original communication and reviewed promise/source links, without silently claiming those extra notes were saved.
- **Evidence library scale:** no dedicated library endpoint exists. The small MVP uses the contracted case list and up to four concurrent detail reads. It fails visibly if an index cannot be loaded instead of implying a partial result is complete. Seed originals are synthetic UTF-8 files with real computed hashes; mock PDFs were replaced with real text originals, not fake PDF bytes.
- **Other surfaces:** no duplicate detection, saved drafts, agenda, inbox, settings or notification endpoints.
- **Complaint export:** contract supports preview text only, no PDF/file export or draft persistence. Copy-to-clipboard is the contracted MVP path.

Implemented mock mutations include create, upload, extract, review, explicit manual entry, full resolution and the local Phase 4 extensions above. Complaint drafting still returns PHASE_NOT_IMPLEMENTED until Phase 5. GAP comments identify unsupported integration boundaries. No backend was changed or verified end to end.
