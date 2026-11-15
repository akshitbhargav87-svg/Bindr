# Parallel implementation contract — planning baseline v1

This is a proposed implementation interface adopted by the two owner prompts, **not a claim these endpoints exist today**. Existing `/api/v1` and `AIModuleAdapter.extract_commitments(...)` remain compatible while new semantics are introduced under versioned interfaces. Before changing a name/type, update this document and golden fixtures together with both owners' review. No unilateral guessed routes.

## Shared transport rules

A implements `/api/v2` for new semantics. B implements a typed v2 client and a test-only HTTP fixture handler at the same paths. Existing v1 behavior remains usable during rollout. Existing session cookies, Origin/CSRF and expected-account headers apply; no user-supplied owner/storage paths. Dates use strict ISO timestamps with explicit offset or `{date, timezone, precision:'date'}`; no naive timestamps. Money is integer minor units plus ISO currency; never float sums/mixed-currency totals.

Writes use `Idempotency-Key` scoped by account+operation and `expected_version` on existing case mutations. A successful exact replay returns the original resource/result without incrementing versions again. Same key/different canonical payload → 409 `IDEMPOTENCY_CONFLICT`. A stale **new** operation → 409 `VERSION_CONFLICT`. Dedupe checks/account authorization precede replay disclosure. Uncertain responses keep the same operation key for reconciliation; no blind create retry. Error envelope preserves `{error:{code,message,details:[{field,message}],request_id}}` without provider secrets.

New v2 case detail returns existing facts plus: `obligations` (individual ID, semantic status, confirmed terms, deadline proposal/override, outcome ledger/balance), `events`, `version`, `projection` (case/obligation status and money-by-currency), `capabilities`. Existing `status=active/superseded/fulfilled` is not silently reused to mean revoked/conditional. Preserve a separate claim/proposal and require a user decision. B never calculates an authoritative overdue status from browser time.

## Agreed interface groups

| Route / seam | Request | Required result / invariant |
|---|---|---|
| POST `/api/v2/cases` | title, merchant_name; operation key | Owned case/version; repeat produces same case |
| POST `/api/v2/cases/{id}/evidence` | Original file, expected_version, JSON metadata `communication` | Immutable original/digest, date/provenance separately; `duplicate_of` within same case or warning, new version only for actual mutation |
| POST `/api/v2/cases/{id}/extractions` | evidence_ids, expected_version, metadata references | Queued job or completed proposal envelope, never confirmed obligations |
| GET `/api/v2/jobs/{id}` | authenticated owner | queued/running/review_required/succeeded/failed/cancelled, stage, safe retryability/error/request ID; reference resource/version |
| POST `/api/v2/cases/{id}/reviews` | expected_version, proposal_id, selected decisions/edited terms, predecessor IDs, deadline override/reason | Transactional confirmations/rejections, old rows retained; closed/stale proposal cannot replay as new facts |
| POST `/api/v2/cases/{id}/manual-promises` | expected_version, terms, source IDs or explicit user_attested origin | Reviewed manual origin; no fake AI quotation/extraction ID |
| POST `/api/v2/deadline-preview` | confirmed communication anchor, expression/parsed duration/range, timezone, calendar ID/version | earliest/latest, condition/anchor_missing, invalid/future warnings, calculation explanation; proposal only |
| POST `/api/v2/cases/{id}/outcomes` | expected_version, obligation allocations, kind partial/full/pending/company_claim/correction, received_at, note, source IDs | Append-only ledger and authoritative balances; claim/pending never closes; corrections reference earlier event |
| POST `/api/v2/cases/{id}/lifecycle` | expected_version, action reopen/archive/restore/edit_identity, reason, edited fields | Preserved history/receipts, explicit reopened obligations; no reset of prior money |
| DELETE `/api/v2/cases/{id}` | expected_version, recent-auth proof/confirmation | Immediately deny normal access; deletion job/token, cancelled dependent jobs; retryable SQL/GCS cleanup, retention explanation |
| GET/PUT `/api/v2/capture-drafts/{id}`; POST `/api/v2/capture-drafts` | owner auth, draft version/operation key, exact capture metadata/text/source references | Account-bound recoverable draft/version. Expired requests deny access; restore only after same-account reauthentication, never cross-account |
| GET `/api/v2/cases/{id}` and `/api/v2/workspace` | owner auth | Consistent case snapshot, per-obligation statuses, totals by currency, server as_of/timezone; review-only records excluded from confirmed money |
| PUT `/api/v2/notification-preferences` | expected preferences version, opt-in channels/timing | Actual capabilities, persisted choice, clear unsupported/unconfigured state |
| POST `/api/v2/cases/{id}/exports`; GET `/api/v2/exports/{id}` | expected_version, selected evidence/facts, reviewed wording, formats pdf/bundle/data | Private snapshot job/download, manifest/digests, stale-facts rejection; no fabricated originals |
| GET `/api/v2/cases/{id}/calendar.ics` | owner auth | Stable UID/timezone/version; static export does not promise live updates |
| POST `/api/v2/account/export`; DELETE `/api/v2/account` | recent auth, confirmation/operation key | Private export or deletion job; revoke access, cancel work, documented backup/third-party retention |
| Connector seams (under `/api/v2/connectors/{provider}`) | connect/status/disconnect; explicit reviewed send/intake operations | A defines provider-specific details in a versioned platform contract before B enables UI. Until then provider-independent UI/state and fixture adapters remain usable |
| Case Q&A seam | POST `/api/v2/cases/{id}/questions`, question + current_version | A retrieves authorized snapshot only, B's pure engine returns answer/citations/abstention; no tool instructions from evidence |

Communication metadata: `{date:null|'YYYY-MM-DD',time:null|'HH:mm:ss',timezone:'Asia/Kolkata',precision:'unknown'|'date'|'timestamp',provenance:'user_confirmed'|'message_metadata'|'extracted',original_wording:null|string}`. Preserve import time separately. Invalid dates produce typed field errors; future communication dates require explicit warning/confirmation policy, not normalization. A deadline conditioned on an unconfirmed event cannot use message date as if the event occurred.

Capture recovery: B can preserve text in account-bound memory immediately, independent of A. Cloud autosave should begin while authenticated before risky work. If a session expires before first save, keep a same-tab recovery buffer outside the auth-keyed subtree and require the same identity before restoring. Do not silently store sensitive capture in persistent browser storage, show it at the login screen or carry it into another account. Files not yet uploaded require explicit reattachment after a full tab/process loss; do not promise impossible persistence.

## Intelligence seam owned by B

Keep the current `AIModuleAdapter.extract_commitments(case_id,evidence,existing_commitments=None,reference_time=None,tz_name='Asia/Kolkata',merchant_name=None)` and its v1 validator behavior intact. Add a separate `extract_proposals_v2(request)` entry point rather than modifying required v1 fields underneath A's callers. A's v2 handler imports that explicit method; A can locally inject an implementation matching its schema.

V2 request is data-only: owned case/evidence IDs selected by A, exact bytes/text with page/message/segment references, per-source communication metadata, relevant confirmed obligations and request/timeout context. B performs bounded document processing and inference, with no database writes, network tools chosen by evidence, storage-path decisions or authorization overrides.

Result shape: `{schema_version:2,proposal_id,candidates:[{candidate_id,terms,sources,temporal,relation,condition,warnings}],document_warnings}`. `terms` retains kind/description/amount_minor/currency and an explicitly proposed due timestamp or null. `sources` carries evidence_id, verbatim quote and page/message/audio offsets. `temporal` preserves exact source wording, candidate anchor/duration/range and parse status; A's deterministic service computes calendar dates from confirmed anchors. `condition` preserves trigger text and known/unknown fulfillment of that trigger. `relation` is new/corroboration/revision/contradiction/cancellation/uncertain with predecessor suggestion and explanation, never an automatic write.

No candidate dropped merely because the first was found. Enforce bounds, segment/de-duplicate long inputs and tell the user when limits prevent full extraction. Impossible dates yield a visible warning and null proposal, not Nov 30/Dec 1. Conditional “initiate refund” is distinct from money received. Reported malformed model output must remain a typed validation failure unless a bounded repair is grounded in the same evidence; never manufacture a successful fallback. Provider diagnostics record stage/duration/request identifiers without raw private evidence/secrets. AI retry is bounded and operation-safe, never a hidden loop of paid calls.

## Golden fixtures and independent tests

Use canonical inputs from `EXTREME_TEST_PACK.md` (all ten + a separately authored dated 1B revision fixture). Preserve Part 1 reported outcomes in `AI_QA_REPORT_SOURCE.md`; original raw provider outputs are missing, so don't invent them. Akshit owns `tests/contracts/platform/`, Tushar `tests/contracts/intelligence/`. Both create valid/invalid/retry/stale/privacy fixtures against this document, keep them in their own tree and exchange hashes/diffs at integration; neither waits on the other to produce files.

Minimum golden cases: four Airtel obligations; conditional unknown trigger; Nov 31 invalid; Dec 28+5 calendar days; conflicting/revoked history; injected HTML/instructions; unknown anchor; same operation replay versus two intentional cases; same PNG duplicate; partial/pending/full/reopen ledger; same-account recovery/different-account denial; old/new deadline reminder cancellation; delete cleanup retries; cross-account export/QA citation rejection. Include 2xx/error/queued-job payloads and v1 compatibility. Contract fixtures are not the production server or semantic AI provider and must be reported as such.

Connector details and export/PDF rendering should not hold up these core fixtures. Later subcontracts must follow the same ownership, versioning, no-automatic-send and explicit-provider-blocker rules. Completing both independent fixture suites is the entry gate to combined testing, not the exit gate from production acceptance.
