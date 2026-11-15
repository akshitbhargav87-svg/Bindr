# Track A verification — 15 November 2026

Result: important local core paths pass. **Not production acceptance.** All tests use synthetic records/documents. Working tree based on `888722d1456380d4c5a370d15f49b7b9ee0d0c16`, branch `codex/platform-reliability`; changes remain uncommitted. Target schema **11**. No frontend/AI implementation or original regression assertions changed; no merge, push, cloud action or deployment.

| Check | Actual result | Scope |
|---|---:|---|
| Complete backend + AI suite | **232 PASS**, 7 warnings, 12.92 s | Includes 59 new platform desired-behavior cases; existing modules tested together |
| Original integration suite | **28 PASS**, 3 warnings, 4.89 s | Unchanged assertions; actual RapidOCR and explicit mock inference |
| Platform contracts + PostgreSQL | **7 PASS**, 1 warning, 1.31 s | 2 fixture/provenance checks + 5 real PostgreSQL 16.2 tests |
| Existing frontend checks | **81 PASS**, no failures/skips | Existing code unchanged |
| Existing frontend build | **PASS**, 1.59 s | Build only; no deployment/container claim |
| Existing frontend adapter → local FastAPI | **PASS** | Real local HTTP: session/create/upload/extract/review/revision/complaint/original/stale-write/resolution |
| v2 HTTP screenshot journey | **PASS**, included above | Real PNG + RapidOCR; explicit test-only AI override; no pre-review obligation; approval/persistence/timeline/original-byte hash |
| Worker + migration CLI | **PASS** | Bounded empty synthetic SQL batch; read-only checker reports schema 11 |
| Start/deploy shell syntax; diff whitespace | **PASS** | Syntax only, no script execution/deployment |

Warnings are deprecations from the existing FastAPI/Starlette/httpx/status-constant combination. They are not failed assertions. One fixture provenance check initially failed because its generator hashed normalized LF text instead of ZIP CRLF bytes; source was verified byte-identical to the ZIP, fixture digest corrected, assertion preserved, and the entire contract/PostgreSQL suite rerun successfully.

The original suites have different scopes; do not combine the counts into a universal security/provider success percentage. Machine-readable results are in `backend-ai-results.xml`, `postgres-results.xml`, `regression-results.xml` beside this report. Local `.log` outputs are retained but ignored by Git.

## Important behavior established

- Same successful operation replays its original result; changed payload conflicts; a different new stale operation fails. Real PostgreSQL overlap produces one matching-operation case and one CAS winner. Two concurrent identical same-case uploads preserve one original/version; separate cases remain independent.
- Four authored canonical Airtel obligations persist together only after review. Selected subset confirmation, closed-proposal replay prevention, invented IDs, negative/fractional money, six malformed AI variants, wrong-evidence quotes, duplicate inputs and timeouts reject without saving facts. Failed attempts retain safe diagnostic IDs/stages, not provider/source bodies. Missing v2 engine fails explicitly; no production mock fallback.
- ₹500 → ₹200 receipt → ₹300 outstanding; pending/company claims do not close it. Full/correction/reopen preserve events/receipts. Currency correction before any receipt cannot relabel later receipts with predecessor currency. New events have causal sequence/version even within one clock second.
- Confirmed anchors/calendars/ranges/year rollover, strict invalid dates, future-source warnings, explicit override reasons and DST ambiguity handling. Original communication metadata changes append before/after history, not altered source files.
- Real SQL Firebase-session boundary with only the external Google provider stubbed: expiry → same-account recovery; different-account denial; revoked-session capture capability denial. Existing forged/expired/Origin/CSRF/security regressions remain green.
- Case deletion immediately denies normal v1/v2 access, then cleans legacy/v2 rows and original/intake objects. Account deletion revokes sessions and purges private local records through a provider-stubbed deletion job. PostgreSQL foreign-key cleanup retains another owner's case.
- Stable reminder IDs, revision cancellation, opt-out, durable retry and uncertain-send reconciliation. Optional email/push/WhatsApp/Gmail adapters are tested with network stubs, never real correspondence.
- Private bundles preserve exact selected originals and hashes. Selected-fact exports omit unrelated amounts/history; readable PDF/preview/QR rendering is checked. QR decodes only to generic instructions, without case access. Synthetic PDF rendering was visually inspected. RFC3161 test uses actual OpenSSL and a synthetic CA, verifying chain/nonce/imprint and rejecting altered/forged data.
- Owner-bound encrypted OAuth/device/phone credentials, one-use OAuth state, provider-signature verification, explicit capture capabilities, thread-only reply dedupe and cross-account webhook partitioning. Intake remains review-only. Private aggregate withdrawal suppresses below-threshold samples; public scoreboard stays disabled.

## Reproduce

Create an isolated Python 3.12 environment; install `backend/requirements-runtime.txt` and `pytest>=8,<9`. Use only a disposable PostgreSQL test URL in `BINDR_TEST_DATABASE_URL`; tests create/remove unique synthetic schemas, never use production. Local verification used PostgreSQL 16.2 from temporary test-only pgserver binaries, which are not a runtime dependency. CI now declares PostgreSQL 16.

```sh
AI_PROVIDER=mock AUTH_PROVIDER=anonymous DATABASE_URL=sqlite:///:memory: \
  OCR_MODEL_DIR=.ocr-models EVIDENCE_STORAGE_DIR=./.venv/test-evidence \
  python -m pytest backend/app/tests backend/app/ai/tests -q

# Set BINDR_TEST_DATABASE_URL securely to a disposable PostgreSQL database first.
AI_PROVIDER=mock AUTH_PROVIDER=anonymous DATABASE_URL=sqlite:///:memory: \
  python -m pytest tests/contracts/platform -q

AI_PROVIDER=mock AUTH_PROVIDER=anonymous ENVIRONMENT=development \
  python scripts/run_integration_regressions.py --source . \
  --auth-hook tests/regression/final_acceptance/signed_session.py \
  --ocr-model-dir .ocr-models
```

OCR assets were prepared using the existing `warm_ocr_models()` helper before the network-blocked regression runner. Frontend commands were unchanged: `npm ci --no-audit --no-fund`, `npm run check`, `npm run build`, then `node checks/live-api.mjs http://127.0.0.1:8019` against a synthetic local server. No credential values are part of the reports.

## Still not accepted

The current real adapter does not yet expose v2 engine methods; fixture engines are not a substitute. B's real v2 client/engine/schema review, mixed-document/audio/multilingual semantics, stored-XSS/remount/two-tab/browser behavior, live Google reset/MFA/cross-device checks, provider configuration/approved controlled delivery, cloud scheduler, backup/restore/soft-delete/orphan review, production-like external races, actual container/integrated CI/deployed revision acceptance remain open. See `OPERATIONS.md` for exact configuration and release gates. No real Meta integration pass or release readiness is claimed.
