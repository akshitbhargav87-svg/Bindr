# Track A implementation status — 15 November 2026

**Core local paths are implemented and verified. This branch is not approved for deployment or full connected product acceptance.** New v2 production intelligence fails explicitly until B's engine connects; manual entry and the existing v1 path remain usable.

Branch: `codex/platform-reliability`, isolated from account head `888722d1456380d4c5a370d15f49b7b9ee0d0c16`. Main at start was `893b80426fd7ddf4e308aa2532c9f49891a61b12`; account PR #4 was open/draft, mergeable, recorded CI successful. Original dirty Desktop/Bindr checkout preserved. No commit, push, merge, deployment, cloud/IAM change or real correspondence performed.

## Verified results

Final machine reports: `docs/platform/backend-ai-results.xml`, `postgres-results.xml`, `regression-results.xml`; local logs with the same names are retained. Frontend check/build/live-adapter logs also reside there. Exact commands are below; final counts are recorded in `docs/platform/VERIFICATION.md`.

- Full backend + AI suite, including new desired-behavior tests.
- All original **28 regressions unchanged**, including real RapidOCR and explicit mock inference.
- **7 platform contract checks**, including **5 actual PostgreSQL 16.2** tests: simultaneous same-key operations, competing case updates, concurrent same-case duplicate upload, populated migration preservation, and legacy/v2/private-intake deletion while another owner's case remains intact. SQLite was not substituted for overlap.
- Existing frontend **81 checks**, build, and its real local v1 HTTP adapter: session, create/upload/extract/review/revise, complaint, original bytes, stale write and resolution. No frontend source changed.
- New v2 HTTP screenshot → actual RapidOCR → explicit test-only mock intelligence → human review → saved obligation/timeline/original digest passes. Real Meta was **not** called or accepted.
- Verified same-account recovery after real SQL session expiry, different-account denial, revocation of capture capabilities, immediate v1/v2 deletion denial, malformed output/citation/candidate/money rejection, partial/full/correction/reopen ledger, stable reminder cancellation, private bundle/selected-fact isolation, QR scope, and synthetic RFC3161 chain/nonce/imprint checks.

## Implemented packets and acceptance boundaries

| Packet | Independent implementation/evidence | Remaining acceptance |
|---|---|---|
| A1 / W1–W2 | Versioned PostgreSQL/SQLite migrations; read-only deployed schema gate; operation replay; private draft recovery; strict communication dates/provenance/correction history; same-case original dedupe | Controlled live Google flows, actual unsaved-before-first-autosave/browser remount behavior, deployment migration rehearsal |
| A2 / W2–W4 | Multi-candidate transaction/review, manual attestation, deterministic date/range/weekend/custom-calendar/clock proposals, persisted assumptions/overrides, append-only money/nonfinancial outcomes, corrections, revision sources, causal event ordering, reopen/archive/notes | Real B engine semantic cases, two real browser tabs and v1-to-v2 fact presentation. Legacy facts are retained separately; legacy receipt money is not invented. |
| A3 / W5, W7, W12 | Durable SQL worker/jobs, stable reminder IDs, opt-in preferences, configured email/FCM/WhatsApp adapters, follow-up prompts, uncertain-send reconciliation, deletion/account cleanup and expiry | Authenticated managed invoker, real delivery/cancellation races at external providers, backup/soft-delete/orphan-retention review |
| A4 / W7, W13 | Private selected PDF/data/original ZIP snapshots, readable paginated ledger/previews, original communication metadata, SHA-256 manifest/offline verifier, generic non-case QR, optional pinned-CA RFC3161 adapter | Actual independent timestamp authority, real cloud private artifacts, production retention and renderer/container acceptance |
| A5 / W6, W9–W10, W12 | Gmail OAuth/custody/reviewed MIME send/bounded thread-only reply polling; verified Resend intake; WhatsApp Business signature/linking/partitioned intake; one-upload extension capabilities; private audio/EML/MSG retention | Provider configuration/approval/live receipts, B capture UI/extension and document/transcription processors. WhatsApp media explicitly requires manual attachment; no personal inbox access. |
| A6 / W8, W11, W13 | Owned bounded retrieval/citation validation with no tools; NCH official-source registry; curated company selection; per-currency receipt counter; private opt-in aggregate threshold/withdrawal | Real grounded B answer engine and adversarial semantics, broader jurisdiction-specific source review where needed; public aggregation/privacy/moderation remains disabled |
| A7 / W1, W13 | Existing auth defenses retained; PostgreSQL overlap and cleanup; credential binding, job bounds, redacted diagnostics, controlled migration/worker tooling | Real Firebase reset/MFA/cross-device, storage recovery/backup restore, distributed abuse/load/external-call race acceptance; no cloud safety claim from local tests |
| A8 / all phases | Canonical ten-input provenance plus separately authored dated 1B; actual HTTP examples/generated v2 schemas; PostgreSQL CI service/checks; operations/release packet | B contract review and combined heads/CI; actual container build, approved staging/production rollout and deployed revision verification |

This covers service implementation across all three roadmap phases. It does **not** label any phase accepted while its required engine/browser/provider/cloud evidence is missing. Long/mixed-document processing, multilingual/audio quality and previously blocked real semantic outputs remain B/combined gates, not successes inferred from fixture engines. Foreground v2 extraction has bounded inference and persisted stage/timing/error records; a general asynchronous long-document extraction pipeline has not been claimed.

## Files and integration packet

New implementation: `backend/app/api/v2/`, `backend/app/services/platform/`, platform/workflow/jobs/integrations/aggregate/pairing/device models, new API schemas, and `backend/migrations/`. Existing owned changes are limited to router/startup registration, model registration, account-deleting checks, provider identity deletion and runtime/build/CI wiring. No B-owned frontend, AI modules, existing `ai_adapter.py` or intelligence files changed. Original regression files and shared contracts are unchanged.

Read `docs/platform/API_V2_PACKET.md` and `CONNECTORS_V1_PROPOSAL.md`; precise request schemas and synthetic response examples are in `tests/contracts/platform/`. These elaborate planning placeholders and need B review before UI activation. Schema target is **11**. Tools: `python -m scripts.migrate_platform --check|--upgrade`, `python -m scripts.platform_worker --max-jobs 20`, `python -m scripts.verify_evidence_bundle BUNDLE.zip`, `python -m scripts.export_platform_contracts`.

## Decision log (recorded once)

- User explicitly adopted the ZIP's Track A implementation prompt. All 22 manifest files were verified. Missing historical chat exports were not supplied/read and did not block independent work. Historical deployment commands were not treated as authorization.
- Preserve Firebase verified identity, revocable SQL sessions, Cloud SQL/private GCS, v1 compatibility, existing secrets/AI configuration and 6–128 password policy. No alternate auth system or public case sharing.
- Keep original QA verdicts immutable. Desired-behavior fixtures are authored tests, not reconstructed missing provider outputs. A fixture digest initially normalized CRLF; its failing provenance assertion led to a raw-byte comparison against the ZIP and corrected fixture hash. The source and assertion were preserved.
- Exact successful operation replay is account-scoped; new stale operations conflict. Failed fact transactions leave no partial proposals/obligations. Separate failed-attempt diagnostics contain only safe stage/time/code/IDs.
- Money uses integer minor units and individual currencies. Pending/company claims are not receipts. The final receipt requires explicit full action; corrections preserve original events. Unpaid currency correction cannot relabel later receipts with the predecessor's currency.
- Unknown dates remain unknown, future source dates remain visible, invalid dates reject, DST ambiguity is not normalized. Weekend-only means no verified regional holiday coverage; saved calendar assumptions/version remain reproducible.
- Evidence is immutable while retained. Deletion is explicit, recent-authenticated and retryable; backups/third-party copies have separate limits. Public aggregates, automatic complaints and unreviewed correspondence stay disabled.
- A owns data/auth/transport; B owns every frontend/engine/processor file. Missing v2 methods fail closed. No fixture fallback exists in deployed configuration.

## Next integration action

Review this branch's v2 packet with B's separately reviewable head, connect the actual engine/client, then run the combined acceptance gates listed in `docs/platform/OPERATIONS.md`. No additional optional feature expansion is needed before those important integration checks. Exact owner configuration/controlled live approvals are listed there; do not request secrets in chat or another Owner grant.
