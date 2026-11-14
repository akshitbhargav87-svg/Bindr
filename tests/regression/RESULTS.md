# Final integration acceptance audit — 14 November 2026

**Decision: functional screenshot integration verified; final acceptance/deployment BLOCKED.** The reported 84-test result is reproducible. The latest pushed AI code adds six passing tests, for 90 native test passes. However, the preserved integration suite has six genuine malformed-output failures plus two obsolete-stub failures, and independent security/upgrade tests expose remaining blockers.

## Exact code and test setup

- Required backend: `2d200017778c01317bf3dc506e76549f833d6eb9`.
- Latest pushed AI at inspection and final head check: `6cd04765d08e5600280e987209ab47f99b9f1ccb` (Meta response schema and deadline fixes). The previously reported `1b0514002f4535baf2544c5fa505b169065e00cb` was also tested for the 84-test comparison.
- Snapshots were retrieved through read-only GitHub connector requests and verified against original Git blob hashes. Assembly happened only in /tmp. No Git fetch/ref update, checkout, merge, branch mutation, production modification or deployment occurred.
- Backend snapshot API/AI contracts match the local contracts byte for byte. All original 28 test cases, helpers and conftest remain byte-for-byte unchanged. The regression runner's only functional change is provisioning a random `AUTH_SECRET` after removing inherited credentials. Signed-session issuance uses production helpers under that private test secret, without overriding authentication. This is trusted synthetic fixture setup, not a login endpoint or evidence of real identity-provider integration.
- Temporary Python 3.12 environment satisfies both snapshots' requirements; `pip check` passes. Real RapidOCR/ONNX assets are available locally. External calls blocked; mock AI explicitly selected; synthetic text/PNG only; no paid Meta request.

## Results

| Run | PASS | FAIL | PENDING |
|---|---:|---:|---:|
| Backend 2d20001 + prior AI 1b05140, complete native suites | 84 | 0 | 0 |
| Backend 2d20001 + latest AI 6cd0476, complete native suites | 90 | 0 | 0 |
| Existing 28 regression cases, latest combined code and signed test sessions | 20 | 8 | 0 |
| Independent signature/expiry/ownership/CSRF/config checks | 7 | 4 | 0 |
| Synthetic legacy-database upgrade | 0 | 1 | 0 |
| Real loopback HTTP screenshot → OCR → mock AI → review | 1 | 0 | 0 |

The 90 native cases comprise **58 backend + 32 AI**. Prior AI had 26 tests. The six additional AI tests cover flat-deadline normalization, missing currency, contradictory/incomplete output, missing category/deadline, non-verbatim quotes and revised-commitment prompt guidance. All passed against exact AI 6cd0476. No failures were suppressed or marked xfail. Raw classifications and dependency versions are in `final_acceptance/results.json`.

The old ac3a916/1b05140 diagnostics were 15 PASS / 13 FAIL under an unverified-session gate; the old strict run was 6 PASS / 3 FAIL / 19 PENDING. The current run uses genuinely signed test sessions and exercises all 28 cases. Its eight failures are not interchangeable with the old unverified-cookie counts.

## Original 28, individually classified

| Test | Status | Evidence / reason |
|---|---|---|
| `test_missing_meta_credentials_never_infers_mock` | PASS | PASS: missing key produces AI_UNAVAILABLE/503, no mock inference or draft. |
| `test_quote_is_linked_to_its_actual_evidence[0]` | FAIL | FAIL: old _get_engine stub is no longer called by per-file pipeline; zero candidates/IndexError. Separate real multi-evidence attribution test passes. Original setup/assertions preserved. |
| `test_quote_is_linked_to_its_actual_evidence[1]` | FAIL | FAIL: old _get_engine stub is no longer called by per-file pipeline; zero candidates/IndexError. Separate real multi-evidence attribution test passes. Original setup/assertions preserved. |
| `test_synthetic_fixture_references[new-refund]` | PASS | PASS: synthetic fixture reference/hash checks only. |
| `test_synthetic_fixture_references[revised-commitment]` | PASS | PASS: synthetic fixture reference/hash checks only. |
| `test_synthetic_fixture_references[overdue-case]` | PASS | PASS: synthetic fixture reference/hash checks only. |
| `test_synthetic_fixture_references[resolved-case]` | PASS | PASS: synthetic fixture reference/hash checks only. |
| `test_invented_candidate_is_rejected` | PASS | PASS: invalid approval rejected without state mutation; top-level validation error. |
| `test_negative_refund_is_rejected[-1]` | PASS | PASS: invalid approval rejected without state mutation; top-level validation error. |
| `test_negative_refund_is_rejected[-499900]` | PASS | PASS: invalid approval rejected without state mutation; top-level validation error. |
| `test_duplicate_evidence_ids_rejected_before_inference` | PASS | PASS: 422 before AI invocation; no mutation. |
| `test_invalid_ai_boundary_output_saves_no_draft[wrong_version]` | PASS | PASS: unsupported schema version rejected with 502, no draft/version mutation. |
| `test_invalid_ai_boundary_output_saves_no_draft[missing_terms]` | FAIL | FAIL: malformed candidate output accepted with 201 instead of 502; schema_version=1 alone is checked before saving. |
| `test_invalid_ai_boundary_output_saves_no_draft[unknown_key]` | FAIL | FAIL: malformed candidate output accepted with 201 instead of 502; schema_version=1 alone is checked before saving. |
| `test_invalid_ai_boundary_output_saves_no_draft[foreign_source]` | FAIL | FAIL: malformed candidate output accepted with 201 instead of 502; schema_version=1 alone is checked before saving. |
| `test_invalid_ai_boundary_output_saves_no_draft[fabricated_quote]` | FAIL | FAIL: malformed candidate output accepted with 201 instead of 502; schema_version=1 alone is checked before saving. |
| `test_invalid_ai_boundary_output_saves_no_draft[invalid_confidence]` | FAIL | FAIL: malformed candidate output accepted with 201 instead of 502; schema_version=1 alone is checked before saving. |
| `test_invalid_ai_boundary_output_saves_no_draft[duplicate_candidate]` | FAIL | FAIL: malformed candidate output accepted with 201 instead of 502; schema_version=1 alone is checked before saving. |
| `test_missing_meta_credentials_http_saves_nothing` | PASS | PASS: missing key produces AI_UNAVAILABLE/503, no mock inference or draft. |
| `test_provider_errors_have_top_level_envelope[AITimeoutError-504-AI_TIMEOUT]` | PASS | PASS: injected provider error has expected status/envelope and no mutation. |
| `test_provider_errors_have_top_level_envelope[AIServiceUnavailableError-503-AI_UNAVAILABLE]` | PASS | PASS: injected provider error has expected status/envelope and no mutation. |
| `test_provider_errors_have_top_level_envelope[AIInvalidOutputError-502-AI_INVALID_OUTPUT]` | PASS | PASS: injected provider error has expected status/envelope and no mutation. |
| `test_review_gate_and_closed_draft[approve]` | PASS | PASS: approval/rejection state and persistence, then 409 closed-draft envelope. |
| `test_review_gate_and_closed_draft[reject]` | PASS | PASS: approval/rejection state and persistence, then 409 closed-draft envelope. |
| `test_revision_preserves_original_evidence_and_history` | PASS | PASS: predecessor history, both evidence IDs and original bytes preserved. |
| `test_anonymous_download_denied` | PASS | PASS: private file denied without authentication, 401 top-level error. |
| `test_real_rapidocr_reads_synthetic_pixels` | PASS | PASS: invalid approval rejected without state mutation; top-level validation error. |
| `test_http_screenshot_real_ocr_mock_ai_then_review` | PASS | PASS: real OCR reads pixels; HTTP workflow reaches reviewed commitment with mock AI. |

Two quotation tests are **reported FAIL**, not silently skipped or fixed in this audit. Their setup monkeypatches `_get_engine`, while the repaired adapter now calls the public per-file pipeline directly. The stale stub is not invoked and actual mock inference yields no candidate for that fixture, producing IndexError. This is a harness compatibility issue, not proof of wrong source attribution. A separate unmodified-production, multi-file HTTP test passes correct quote/evidence association. Future test maintenance should move only the inference stub to the actual public per-file seam while retaining all existing source-ID/quote assertions.

The other six failures are actual boundary-validation gaps: missing terms, unknown candidate keys, foreign evidence references, fabricated quotations, confidence >1 and duplicate candidate IDs are saved as drafts (201). Wrong schema_version is now rejected (502). Meta-provider response validation does not replace validation of the complete candidate envelope before database persistence.

## Verified functional integration

A real Uvicorn server bound only to loopback ran with an ephemeral private test signing secret and explicit `AI_PROVIDER=mock`. A trusted test fixture issued a session using the production helper; no login route or auth override was added.

- Anonymous case read: 401. Arbitrary forged session: 401.
- Signed case create: 201; PNG upload: 201; extraction: 201; review: 200.
- **One actual RapidOCR inference and one actual deterministic MockAIProvider call**, observed without substituting OCR output.
- No commitment existed before explicit review. Afterwards the case contained one reviewed refund for 15,000 minor units with the original evidence UUID and extraction UUID.
- Evidence download matched the original PNG bytes and SHA-256. Quote belonged to the cited evidence and recognized source text.
- Case timeline contained `case_created`, `evidence_uploaded`, `extraction_created`, `commitment_created`.

**Timeline WARNING:** this run displayed `evidence_uploaded` before `case_created`. Timestamps have second precision and ties are sorted by UUID. Event presence and persistence pass; causal ordering within a second is not guaranteed. Add an event sequence or finer timestamps before relying on displayed order for audit chronology.

Original approval/rejection, closed-draft replay rejection and revised-history/original-evidence preservation regressions also pass. The API's screenshot support is exercised as requested; the shared API upload contract still lists text/PDF, so formal contract adoption remains outstanding and was not edited.

## Independent security outcomes

| Check | Status | Evidence |
|---|---|---|
| Anonymous access | PASS | Case and private evidence requests denied with 401 |
| Random cookie / random bearer | PASS | Neither is accepted as identity; both return 401 |
| Signed token with modified user ID | PASS | Signature check rejects it, 401 |
| Cross-user case, evidence, extraction, review, commitment, revision and timeline access | PASS | Two production-signed synthetic identities; other user's IDs return 404, list excludes their cases |
| Missing and incorrect CSRF headers for cookie mutation | PASS | Both return 403 CSRF_FAILED |
| Year-old signed session | **FAIL — HIGH** | Returns 200; timestamp is parsed/signed but never checked for maximum age |
| Session dated one year in future | **FAIL — HIGH** | Returns 200; no validity window/clock-skew check |
| Untrusted Origin with valid cookie+CSRF | **FAIL — HIGH** | Mutation returns 201; Origin requirement is not enforced |
| Missing deployment signing secret | **FAIL — CRITICAL** | Auth module imports successfully with no AUTH_SECRET and uses a built-in fallback; default key material is not reproduced here |

These checks use production verification and owner filters, not `get_current_session` overrides. Positive results apply under the explicitly provisioned private test key. No hardcoded or mere-presence token was treated as authentication proof. Real browser login/bootstrap remains PENDING. A default public signing key can defeat otherwise-correct HMAC checks if deployment omits the expected environment variable.

Relevant backend locations: `core/auth.py:23` (secret fallback), `:40-61` (signature without expiry), `:78` onwards (CSRF but no Origin validation), `models/case.py:16` (new owner_id), and owner filters throughout API endpoints. Session revocation/logout/account-disable behavior is not implemented or verified.

## Seven reported warnings

The reported seven warnings were reproduced in **both** the 84- and 90-test native runs. They are seven occurrences of three deprecation messages, not seven hidden test failures.

| # | Trigger | Severity | Assessment / later action |
|---:|---|---|---|
| 1 | Starlette TestClient using httpx | LOW — test tooling | Pin a tested compatible transport combination; plan the supported replacement before removing the old transport |
| 2 | audit_repairs: duplicate evidence, deprecated HTTP_422_UNPROCESSABLE_ENTITY alias | LOW — maintenance | Replace alias with supported equivalent; numeric status remains 422 |
| 3 | integration_defects: invented candidate, same 422 alias | LOW — maintenance | Same |
| 4 | integration_defects: zero/negative refund, same 422 alias | LOW — maintenance | Same |
| 5 | integration_defects: duplicate review candidate, same 422 alias | LOW — maintenance | Same |
| 6 | evidence: empty upload, same 422 alias | LOW — maintenance | Same |
| 7 | evidence: oversized upload, deprecated HTTP_413_REQUEST_ENTITY_TOO_LARGE alias | LOW — maintenance | Replace alias with supported equivalent; numeric status remains 413 |

Warnings 2–6 are five occurrences of the same alias deprecation. None caused current failures. They are lower priority than the independently observed security, schema-validation and migration blockers. No dependency or production-code fix was attempted.

## Missing bootstrap, migration and deployment requirements

**BLOCKER: session lifecycle and secure bootstrap.** There is a Python signing helper, not an external login/session-bootstrap flow. Supply a trusted identity-to-user mapping, supported issuance/login endpoint or host integration, secure HttpOnly/Secure/SameSite session cookie handling, readable CSRF bootstrap, expiry/future-skew policy and revocation/logout behavior. Require private `AUTH_SECRET` at startup with no built-in fallback. Docs currently say `SESSION_SECRET`; implementation reads `AUTH_SECRET`. Reconcile the mapping explicitly without exposing a signing key to the frontend. Auth fixtures cannot certify browser login or cookie issuance flags.

**BLOCKER for upgrades: migrations and ownership backfill.** Production startup calls `Base.metadata.create_all`, which does not alter existing tables. A synthetic legacy cases table remained without owner_id after that exact operation. Add a versioned migration and deliberate owner assignment/backfill for existing cases; do not blindly assign private customer cases to a demo user. Rehearse backup/restore and upgrade before pointing at existing data. Fresh in-memory tests do not validate migrations. PostgreSQL driver, migration commands, TLS settings and a PostgreSQL run are still missing/unverified; test results here use SQLite only.

**BLOCKER before deployment: environment and storage wiring.** Install both backend and AI requirement manifests; backend requirements alone omit AI/OCR packages. Pin tested dependencies and include OCR runtime/model assets in the deploy image. Map actual `MODEL_API_KEY`, `META_MODEL`, `META_BASE_URL` and timeout settings to the documented logical AI settings. Storage implementation uses `EVIDENCE_STORAGE_DIR`, while docs describe `EVIDENCE_LOCAL_DIR`/driver settings; confirm one effective private persistent directory or implement the chosen backend. No S3, persistent-volume restore, or production credentials were exercised.

**BLOCKER before browser release: Origin/CORS and routing.** Replace wildcard credentialed CORS with explicit deployment origins, validate Origin on cookie mutations, and verify same-origin `/api/v1` proxy or frontend build URL mapping. Session bootstrap must supply the CSRF token without exposing auth secrets. No frontend module or hosting deployment was changed/tested here.

**PENDING: real Meta and staging/deployment acceptance.** New Meta schema/deadline tests are deterministic mocked HTTP tests. No actual paid Meta request was sent, so live access/model eligibility/rate limits/provider privacy/deployment networking are not certified. Do not infer them from mock success.

## Required fixes before final acceptance

1. Validate the full extraction candidate schema and source membership/quotes before saving, not only schema_version. Keep the six failing regression assertions.
2. Require a private signing secret; add session expiry and future timestamp checks, revocation policy, and trusted browser bootstrap.
3. Enforce Origin and restrict credentialed CORS.
4. Provide and test database migration/backfill and the real persistent deployment configuration.
5. Maintain the two obsolete quote-test stubs at the new per-document inference seam, retaining every assertion; this audit left them unchanged and reports their failures.

All production fixes remain with module owners. The screenshot chain, ownership filters, missing-key behavior, approval/rejection, duplicate evidence rejection, version rejection and tested error envelopes are independently verified. Passing native suites do not override the remaining failures.

## Reproduction and evidence

Test-only support: `final_acceptance/signed_session.py`, `security_checks.py`, `deployment_checks.py`; scripts: `run_signed_http_acceptance.py`, `run_acceptance_suites.py`. Supplemental check filenames are explicitly selected and do not change default collection of the original 28.

```sh
python scripts/run_integration_regressions.py --source /tmp/bindr-acceptance-combined --auth-hook tests/regression/final_acceptance/signed_session.py --junit /tmp/bindr-regressions.xml
python scripts/run_acceptance_suites.py /tmp/bindr-acceptance-combined /tmp/bindr-native.xml backend/app/tests backend/app/ai/tests
python scripts/run_acceptance_suites.py /tmp/bindr-acceptance-combined /tmp/bindr-security.xml /absolute/repository/tests/regression/final_acceptance/security_checks.py --bindr-source /tmp/bindr-acceptance-combined
python scripts/run_acceptance_suites.py /tmp/bindr-acceptance-combined /tmp/bindr-migration.xml /absolute/repository/tests/regression/final_acceptance/deployment_checks.py --bindr-source /tmp/bindr-acceptance-combined
python scripts/run_signed_http_acceptance.py --source /tmp/bindr-acceptance-combined --report /tmp/bindr-real-http.json
```

Recorded interpreter: `/tmp/bindr-audit-py312/bin/python`. Snapshots contain no .env. Test helper issuance is not public bootstrap. The original runner gained only ephemeral test-secret provisioning; original test files/helpers/conftest and contracts were preserved. No deployment or Git mutation was performed. Stop after verification report.

---

## Archived preceding audits

# Latest integration re-audit — 14 November 2026

**Verdict: FAIL — integration remains blocked.** Some original validation/error defects are fixed in route diagnostics, but genuine authenticated acceptance is PENDING, text extraction now fails at the backend/AI interface, and HTTP screenshots still bypass the real OCR engine.

## Exact sources and isolation

- Backend: `ac3a916936e2ed551e7e5f5a7b60e61300da674e`.
- AI: `1b0514002f4535baf2544c5fa505b169065e00cb`.
- GitHub connector read exact commits; no fetch, checkout, branch/ref update or Git mutation. Snapshot files were verified against Git blob hashes before assembly. Latest AI directory overlays the backend snapshot only in `/tmp/bindr-reaudit-combined`; neither developer's production files were edited.
- API_CONTRACT.md and AI_CONTRACT.md in the backend snapshot exactly match the local contracts. All original `test_*.py` files, helpers, and the regression runner retain their pre-audit SHA-256 hashes. No assertions were weakened. Snapshot-specific hooks only label missing authentication or exercise the existing weak token gate for diagnostics; no auth dependency override is used.
- Reused isolated Python 3.12 environment `/tmp/bindr-audit-py312`. Installing both snapshots' declared requirements with `pip install --no-index ...` confirmed installed dependencies satisfy them; `pip check` passed. Exact tested versions and per-test classifications are in `reaudit_support/results.json`.
- Synthetic text and generated screenshot pixels only. Temporary SQLite/storage. Paid/external network calls blocked in tests and audit server; no real Meta request. No deployment/PostgreSQL readiness claim.

## Actual execution totals

| Run | PASS | FAIL | PENDING | Meaning |
|---|---:|---:|---:|---|
| Old baseline, anonymous diagnostic | 8 | 20 | 0 | Backend 02e1b4b + AI 9ec0eda; unauthenticated route mechanics only |
| Latest original 28, strict acceptance | 6 | 3 | 19 | Auth-required workflows cannot establish a valid identity |
| Latest original 28, unverified-session diagnostic | 15 | 13 | 0 | Random unregistered cookie passes existing production gate; **not authenticated acceptance** |
| Complete backend suite on combined code | 31 | 19 | 0 | All 50 cases executed; its native fixture uses an arbitrary preset cookie, not verified authentication |
| Complete AI suite on combined code | 26 | 0 | 0 | All 26 cases executed, including real RapidOCR and mocked Meta transport |
| Supplementary security probes | 0 | 6 | 0 | Forged credentials, anonymous case/commitment routes, missing owner field |

There were no collection/setup errors. pytest failures are actual failed assertions or the production TypeError, not missing code or suppressed xfails. Deprecation warnings from Starlette/httpx did not cause failures.

Nine formerly failing original cases now pass in diagnostics: invented candidate (1), negative amounts (2), provider error envelopes (3), closed-draft error envelopes (2), and no-token private download (1). Two formerly passing adapter cases now fail (missing credentials and first-evidence quote) because the new pipeline invocation is incompatible. The other eleven previously failing cases remain failing. Counts are not a security acceptance score.

## Original 28 cases, individually classified

Acceptance leaves auth-dependent cases PENDING even when their diagnostic assertions pass. Diagnostic failures are reported separately rather than reclassified as pending. Full module-suite case names/statuses/reasons are also recorded individually in `reaudit_support/results.json`.

| Original test case | Old diagnostic | Latest acceptance | Latest diagnostic | Specific reason / limit |
|---|---|---|---|---|
| `test_missing_meta_credentials_never_infers_mock` | PASS | FAIL | FAIL | FAIL: incompatible evidence= pipeline call raises TypeError before adapter mapping/credential handling. |
| `test_quote_is_linked_to_its_actual_evidence[0]` | PASS | FAIL | FAIL | FAIL: incompatible evidence= pipeline call raises TypeError before adapter mapping/credential handling. |
| `test_quote_is_linked_to_its_actual_evidence[1]` | FAIL | FAIL | FAIL | FAIL: incompatible evidence= pipeline call raises TypeError before adapter mapping/credential handling. |
| `test_synthetic_fixture_references[new-refund]` | PASS | PASS | PASS | Offline fixture or standalone real RapidOCR assertions pass. |
| `test_synthetic_fixture_references[revised-commitment]` | PASS | PASS | PASS | Offline fixture or standalone real RapidOCR assertions pass. |
| `test_synthetic_fixture_references[overdue-case]` | PASS | PASS | PASS | Offline fixture or standalone real RapidOCR assertions pass. |
| `test_synthetic_fixture_references[resolved-case]` | PASS | PASS | PASS | Offline fixture or standalone real RapidOCR assertions pass. |
| `test_invented_candidate_is_rejected` | FAIL | PENDING | PASS | Valid session bootstrap unavailable; diagnostic uses an unregistered synthetic token only. Route assertions pass; authentication/ownership not accepted. |
| `test_negative_refund_is_rejected[-1]` | FAIL | PENDING | PASS | Valid session bootstrap unavailable; diagnostic uses an unregistered synthetic token only. Route assertions pass; authentication/ownership not accepted. |
| `test_negative_refund_is_rejected[-499900]` | FAIL | PENDING | PASS | Valid session bootstrap unavailable; diagnostic uses an unregistered synthetic token only. Route assertions pass; authentication/ownership not accepted. |
| `test_duplicate_evidence_ids_rejected_before_inference` | FAIL | PENDING | FAIL | Valid session bootstrap unavailable; diagnostic uses an unregistered synthetic token only. Diagnostic still returns 201 instead of rejecting invalid data. |
| `test_invalid_ai_boundary_output_saves_no_draft[wrong_version]` | FAIL | PENDING | FAIL | Valid session bootstrap unavailable; diagnostic uses an unregistered synthetic token only. Diagnostic still returns 201 instead of rejecting invalid data. |
| `test_invalid_ai_boundary_output_saves_no_draft[missing_terms]` | FAIL | PENDING | FAIL | Valid session bootstrap unavailable; diagnostic uses an unregistered synthetic token only. Diagnostic still returns 201 instead of rejecting invalid data. |
| `test_invalid_ai_boundary_output_saves_no_draft[unknown_key]` | FAIL | PENDING | FAIL | Valid session bootstrap unavailable; diagnostic uses an unregistered synthetic token only. Diagnostic still returns 201 instead of rejecting invalid data. |
| `test_invalid_ai_boundary_output_saves_no_draft[foreign_source]` | FAIL | PENDING | FAIL | Valid session bootstrap unavailable; diagnostic uses an unregistered synthetic token only. Diagnostic still returns 201 instead of rejecting invalid data. |
| `test_invalid_ai_boundary_output_saves_no_draft[fabricated_quote]` | FAIL | PENDING | FAIL | Valid session bootstrap unavailable; diagnostic uses an unregistered synthetic token only. Diagnostic still returns 201 instead of rejecting invalid data. |
| `test_invalid_ai_boundary_output_saves_no_draft[invalid_confidence]` | FAIL | PENDING | FAIL | Valid session bootstrap unavailable; diagnostic uses an unregistered synthetic token only. Diagnostic still returns 201 instead of rejecting invalid data. |
| `test_invalid_ai_boundary_output_saves_no_draft[duplicate_candidate]` | FAIL | PENDING | FAIL | Valid session bootstrap unavailable; diagnostic uses an unregistered synthetic token only. Diagnostic still returns 201 instead of rejecting invalid data. |
| `test_missing_meta_credentials_http_saves_nothing` | FAIL | PENDING | FAIL | Valid session bootstrap unavailable; diagnostic uses an unregistered synthetic token only. Diagnostic returns 500, expected 503. |
| `test_provider_errors_have_top_level_envelope[AITimeoutError-504-AI_TIMEOUT]` | FAIL | PENDING | PASS | Valid session bootstrap unavailable; diagnostic uses an unregistered synthetic token only. Route assertions pass; authentication/ownership not accepted. |
| `test_provider_errors_have_top_level_envelope[AIServiceUnavailableError-503-AI_UNAVAILABLE]` | FAIL | PENDING | PASS | Valid session bootstrap unavailable; diagnostic uses an unregistered synthetic token only. Route assertions pass; authentication/ownership not accepted. |
| `test_provider_errors_have_top_level_envelope[AIInvalidOutputError-502-AI_INVALID_OUTPUT]` | FAIL | PENDING | PASS | Valid session bootstrap unavailable; diagnostic uses an unregistered synthetic token only. Route assertions pass; authentication/ownership not accepted. |
| `test_review_gate_and_closed_draft[approve]` | FAIL | PENDING | PASS | Valid session bootstrap unavailable; diagnostic uses an unregistered synthetic token only. Route assertions pass; authentication/ownership not accepted. |
| `test_review_gate_and_closed_draft[reject]` | FAIL | PENDING | PASS | Valid session bootstrap unavailable; diagnostic uses an unregistered synthetic token only. Route assertions pass; authentication/ownership not accepted. |
| `test_revision_preserves_original_evidence_and_history` | PASS | PENDING | PASS | Valid session bootstrap unavailable; diagnostic uses an unregistered synthetic token only. Route assertions pass; authentication/ownership not accepted. |
| `test_anonymous_download_denied` | FAIL | PASS | PASS | No-token private download now returns 401 with the contract error envelope; forged-token bypass remains. |
| `test_real_rapidocr_reads_synthetic_pixels` | PASS | PASS | PASS | Offline fixture or standalone real RapidOCR assertions pass. |
| `test_http_screenshot_real_ocr_mock_ai_then_review` | FAIL | PENDING | FAIL | Valid session bootstrap unavailable; diagnostic uses an unregistered synthetic token only. Diagnostic observes zero OCR calls; real HTTP extraction returns 422. |

## Real HTTP screenshot attempt

Executed `scripts/run_http_screenshot_audit.py` against a real Uvicorn listener on loopback, not merely a function call or fabricated OCR response. The test server uses the unchanged production auth dependency, real OCR observers and deterministic MockAIProvider; original evidence is synthetic PNG pixels.

- Case creation without credentials: HTTP 201 (security defect).
- Screenshot upload without credentials: HTTP 401 (narrow missing-token check works).
- Screenshot upload with a newly generated, never-registered cookie: HTTP 201 (authentication bypass).
- Extraction: **FAIL**, HTTP 422 `UNREADABLE_EVIDENCE`; real RapidOCR calls **0**, mock AI calls **0**.
- Draft review: **PENDING**, because extraction created no draft. The complete requested pipeline did not pass. Independent real OCR tests pass; they cannot substitute for HTTP wiring.

Machine-readable result is in `reaudit_support/results.json` under `real_http`. No token values, private document data or server logs are included.

## Security findings

**FAIL: authentication is only a nonempty-token gate.** `backend/app/core/auth.py:29-64` reads cookie, bearer or session headers and constructs a user ID from the token prefix. It does not look up a session, verify a signature, check expiry/revocation, or validate a user. Both randomly generated cookie and bearer values retrieve private evidence with HTTP 200. A hardcoded demo/test token is not a valid authentication implementation and was not accepted as evidence of one.

**FAIL: incomplete route protection and no case ownership.** Anonymous GET/POST `/api/v1/cases` returns 200/201. Anonymous POST `/api/v1/cases/{id}/commitments` returns 201. `backend/app/models/case.py` has no `owner_id`; therefore a genuine two-user authorization test is PENDING until verifiable identities and owner relationships exist. No-token evidence access now returns 401, but private evidence remains accessible with arbitrary nonempty credentials.

Authenticated workflow acceptance remains PENDING; CSRF and identity isolation are not established by any diagnostic cookie. Native backend test passes do not change this assessment.

## Required fixes, assigned to module owners

1. **Blocker — align actual AI interface.** Backend `backend/app/services/ai_adapter.py:239-248` calls `extract_commitment_from_evidence(evidence=..., existing_commitments=..., reference_time=..., timezone=...)`. Actual AI `backend/app/ai/engine.py:174-183` requires `file_source` plus filename/evidence_id/metadata/provider/timeout and returns a `CommitmentExtractionResult`, not the contract candidates dictionary. Translate per-document inputs and outputs explicitly, preserve evidence references, and apply provider/credential/error handling before inference. Do not mask the TypeError with a fallback. This currently causes HTTP 500 instead of a draft or missing-credentials 503.
2. **Blocker — connect OCR to its real implementation.** Backend adapter `:75-80` imports `backend.app.ai.ocr.extract_text_from_file`; no such module exists in the AI tree. AI exposes `DocumentProcessor.process_bytes` and `extract_commitment_from_evidence`. Use the existing implementation; map unreadable-document failures appropriately. HTTP PDF extraction shares this wrong entry point.
3. **Blocker — implement real sessions and ownership.** Validate identity, expiry/revocation and CSRF; apply ownership filters to all case/evidence/extraction/commitment routes. Do not rely on hardcoded or arbitrary cookie/header values. Add genuine two-user tests once setup is available.
4. **Blocker — validate invalid output at the persistence boundary.** Backend `backend/app/api/endpoints/extractions.py:155-156` saves candidates without validating the full envelope, schema version, required/extra keys, source references/quotes, confidence or uniqueness. All seven malformed-boundary cases still return 201. Preserve the existing fail-closed regression assertions.
5. **Blocker — reject duplicate evidence before invoking AI.** Backend request schema/route checks count but not uniqueness. A valid stub result still creates a draft for duplicate IDs, bypassing the adapter's later check. Reject with 422 and no version/draft mutation before the adapter is called.
6. **Partially verified — quote mapping and Meta failures.** Per-file quote checks and explicit missing-key guards exist, but the incompatible pipeline call runs first. Original quote and credential-path regressions fail; do not claim these integrated behaviors fixed until the signature/return translation is corrected and rerun.

Verified route fixes: candidate membership and negative amount rejection; top-level 502/503/504 and closed-draft error envelopes when injected errors reach handlers; predecessor/original evidence history retention. These checks use a valid synthetic draft stub where specified in the unchanged suite. Full unmocked extraction → review remains blocked. General malformed-JSON/405/CORS/security behavior beyond these cases is not certified.

## Reproduction

Use the existing runner with the credential-free assembled source and the snapshot-specific hooks:

```sh
python scripts/run_integration_regressions.py --source /tmp/bindr-reaudit-combined --auth-hook tests/regression/reaudit_support/valid_auth_required.py --junit /tmp/bindr-acceptance.xml
python scripts/run_integration_regressions.py --source /tmp/bindr-reaudit-combined --auth-hook tests/regression/reaudit_support/unverified_session_diagnostic.py --junit /tmp/bindr-diagnostic.xml
python scripts/run_module_audit.py /tmp/bindr-reaudit-combined /tmp/bindr-backend.xml backend/app/tests
python scripts/run_module_audit.py /tmp/bindr-reaudit-combined /tmp/bindr-ai.xml backend/app/ai/tests
python scripts/run_module_audit.py /tmp/bindr-reaudit-combined /tmp/bindr-security.xml /absolute/repository/tests/regression/reaudit_support/security_probes.py --bindr-source /tmp/bindr-reaudit-combined
python scripts/run_http_screenshot_audit.py --source /tmp/bindr-reaudit-combined --report /tmp/bindr-http.json
```

Use `/tmp/bindr-audit-py312/bin/python` for the recorded environment. The unverified hook is intentionally a vulnerability diagnostic, never a valid auth fixture; remove its use for acceptance once real authentication exists. Existing runner and all original regression assertions were preserved. New supplementary security probes are explicitly selected and do not change the default 28-case collection. No production or contract fixes were attempted.

---

## Archived original baseline

# Regression execution — 14 November 2026

Sources: backend `02e1b4b0a7c3cd2fec57b0bb66e69b9709b809c3`, AI `9ec0eda8af8564b28a49bcedb2a506c61fdcba10`. Contracts unchanged; provenance and commands in README.md. Tests are local/in-process, temporary SQLite/storage, paid network calls blocked. No real Meta request was attempted.

| Run | Passed | Failed | Pending/skipped |
|---|---:|---:|---:|
| Current integration checkout (no backend source) | 4 | 0 | 24 |
| Pinned combined sources, default mode | 7 | 2 | 19 |
| Pinned combined sources, explicit anonymous diagnostic mode | 8 | 20 | 0 |

Default pending reasons: protected routes need an agreed session/CSRF bootstrap. The HTTP screenshot workflow is included among those 19 pending tests. The local checkout's 24 pending tests require unavailable backend/AI modules. These skips are not passes. Diagnostic mode is route-behavior verification only, not authenticated integration.

## Verified

- Explicit Meta mode with missing credentials raises AI_UNAVAILABLE without mock inference at the adapter boundary. The HTTP diagnostic returns 503 and saves no draft; its error envelope still fails the contract.
- First-document quotation mapping passes; four existing synthetic JSON fixtures pass reference/hash/source checks.
- Independent real RapidOCR recognition of synthetic screenshot pixels passes. The HTTP route does not invoke it.
- Revised commitment history, original evidence bytes, and both original/new evidence IDs are preserved in the HTTP diagnostic.
- Approval and rejection behavior succeeds before those two tests fail on the repeated-review error envelope.

## Failing expectations in diagnostic mode (20 test cases)

- Correct evidence association when quotation belongs to the second document: 1.
- Invented candidate rejection: 1.
- Negative financial amount rejection: 2.
- Duplicate evidence IDs rejected before AI invocation: 1.
- Malformed AI output rejected before persistence: 7.
- Missing-credentials HTTP error format: 1.
- Provider failure error formats: 3.
- Closed approval/rejection draft error formats: 2.
- Anonymous private-evidence access denied: 1.
- HTTP screenshot route invokes real RapidOCR: 1.

Remaining fixes belong to module owners: wire document processing into HTTP extraction; validate quotes per evidence and validate full AI outputs; enforce candidate membership and money bounds; reject duplicate evidence before inference; protect evidence with authentication; normalize errors at top level. No fixes were implemented. One Starlette/httpx deprecation warning was emitted; it did not cause failures. Dependencies were installed only into /tmp; no production manifest changed.
