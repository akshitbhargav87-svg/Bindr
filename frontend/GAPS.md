# Integration gaps

Contract snapshot: feature/integration @ 70f2db0, version 1. No endpoints invented.

Phase 2 update: the dashboard and case list are implemented through a workspace read service. HTTP mode combines the contracted list and bounded detail reads; there is no invented aggregate endpoint. Rich mock status is computed in the mock adapter. HTTP status stays server-provided, with missing dates displayed as Needs a date. No browser-clock overdue/due-today calculation was added. Reference date, server timezone metadata and Due today remain contract gaps. Capture, original file viewing, case mutations and writable settings remain their later phases. See PHASE-2-HANDOVER.md.

- **Session bootstrap:** contracts require authenticated cookies + CSRF, while the product prompt requests no auth UI. Backend must supply the session outside the domain API. HTTP adapter carries cookies and echoes CSRF; no credentials are hardcoded.
- **Images/OCR:** backend accepts only text/plain and text-layer PDF, max 10 MiB per file. PNG/JPEG extraction requires backend support; do not present images as accepted in HTTP mode.
- **Communication dates/calendar:** uploads accept only file + expected_version. No occurred_at field or deterministic relative-date calculation response is contracted. Mock-only calendar behavior must not leak into components.
- **Rich status labels:** API case status is open/overdue/resolved. Due today/needs a date needs backend enrichment for production; do not derive authoritative status using a browser clock.
- **Case list summaries:** list returns no commitment amount/deadline; aggregate fields or detail reads will be needed.
- **Manual entry:** review requires an existing extracted candidate; there is no endpoint to persist an independent manual commitment after extraction failure.
- **Case lifecycle:** no partial outcome, reopen, edit, archive/restore or delete endpoints.
- **Other surfaces:** no duplicate detection, saved drafts, agenda, inbox, settings or notification endpoints.
- **Complaint export:** contract supports preview text only, no PDF/file export or draft persistence. Copy-to-clipboard is the contracted MVP path.

Phase 1 has no live case writes. Mock mutation methods explicitly return PHASE_NOT_IMPLEMENTED until the corresponding workflow phase is built. GAP code comments will be added at the relevant implementation boundary as each surface is implemented.
