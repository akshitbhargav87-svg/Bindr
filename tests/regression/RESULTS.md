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
