# Resume Bindr extreme testing — 15 November 2026

## Resumed result — supersedes pending status below

Dedicated testing is recorded in `EXTREME_TEST_REPORT.md`: **16 PASS, 5 FAIL, 4 PARTIAL, 1 BLOCKED** across 26 criteria. Real reset-email use/reuse still needs a controlled inbox/account. Clean final execution: 18 backend probes passed in 2.42s and 6 React/projection probes passed in 2.73s. Probe success includes assertions confirming product shortcomings; it does not mean every requested feature passed.

Sources: `backend/app/tests/test_extreme_pack.py`, `frontend/checks/extreme-pack.test.mjs`. Final logs/XML/JSONL are in the existing evidence directory. Read-only live health/config/action-route/unauthenticated checks passed (`live-http-resumed.json`). No product or production changes were made. Next step is controlled live reset testing or separately authorized fixes. Everything below is the earlier saved stopping-point history, superseded where it says no dedicated probes exist or all scenarios are pending.

## Active request

The user supplied `EXTREME_TEST_PACK.md` and asked for the easiest/fastest way to run all remaining tests and create a report. **Part 1 means the ten AI promise-extraction stress tests; the user already completed them. Do not rerun those.** It does not mean implementation Phase 1. Parts 2 and 3 contain 16 + 10 = **26 remaining scenarios**. Part 4 only prioritizes Part 1 tests and adds no new scenarios.

The user then asked to save progress immediately and said they would continue shortly. This file records the exact stopping point. No feature fixes or deployment changes were made during testing.

## Repository and artifacts

- Active checkout: `C:\Users\Test\OneDrive\Documents\ChatGPT\PromiseKeeper - VIHAANX\bindr-google-cloud`.
- Branch `codex/account-auth`, HEAD `888722d1456380d4c5a370d15f49b7b9ee0d0c16`. GitHub branch listing was rechecked and still matches; main remains `893b804`.
- Original test attachment: `C:\Users\Test\.codex\attachments\f45c62e5-c50f-4544-aade-45047ea62787\Pasted text.txt`; copied to `docs/EXTREME_TEST_PACK.md`.
- Working report: `docs/EXTREME_TEST_REPORT.md`.
- Logs/evidence: `storage/extreme-testing-2026-11-15/` (ignored by Git).
- Existing authentication/resume edits and product-roadmap files remain local/uncommitted. Preserve all of them. No test harness for the 26 dedicated scenarios has been written yet.

## Completed runs

1. **Backend baseline: 124 passed, 6 deprecation warnings, 15.12 seconds.** Ran `backend/app/tests` only, not the ten user-completed Part 1 fixtures or the separate AI test suite. Raw log: `backend-baseline.log`; machine-readable result: `backend-baseline.xml` in the evidence directory.
2. **Frontend baseline: 81 passed, 0 failed, 5.43 seconds.** Raw log: `frontend-baseline-unrestricted.log`.
3. Initial restricted frontend run had 80 passes and one `fetch failed`; isolated rerun also failed. A minimal localhost server/fetch probe established `connect EACCES 127.0.0.1:<port>`. The restricted Python TestClient suite stalled for the same loopback restriction. Those stalled runs were interrupted through their own exec sessions.
4. Both suites were rerun with `sandbox_permissions: require_escalated` to allow localhost networking; both passed. These were environment failures, not demonstrated product regressions. All test processes have completed; there is no running test session to resume.
5. Three lightweight production reads (`/health`, `/api/v1/auth/config`, `/auth/action`) were attempted from the restricted shell and all failed DNS (`getaddrinfo failed`). See `live-http.json`. This does not establish live-service failure. Browser/live verification has not been attempted in this testing request.

## Test execution setup that worked

Use the existing `.venv\Scripts\python.exe` (Python 3.13.7 here), Node 22.17.0 and installed frontend dependencies. No dependency installation was needed. Set process-local environment before Python tests:

```text
DATABASE_URL=sqlite:///C:/Users/Test/OneDrive/Documents/ChatGPT/PromiseKeeper - VIHAANX/bindr-google-cloud/storage/extreme-testing-2026-11-15/baseline.db
ENVIRONMENT=development
AUTH_PROVIDER=anonymous
AI_PROVIDER=mock
OCR_MODEL_DIR=<absolute repository path>/.ocr-models
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
OMP_NUM_THREADS=1
```

Commands, from repository root (frontend command from `frontend/`):

```text
.venv\Scripts\python.exe -u -m pytest backend/app/tests -q --junitxml=storage/extreme-testing-2026-11-15/backend-baseline.xml
npm run check
```

A normal sandbox run cannot perform the loopback connections needed by FastAPI TestClient/Node contract-server fetch on this host. Use the working escalation when needed and explain its concrete localhost reason. Temporary SQLite and temporary evidence storage isolate the tests. Existing account tests stub Google's external identity provider while exercising real FastAPI routes/SQL; do not call them real Firebase login tests.

## Fastest remaining approach

Build one repeatable, isolated API/SQL probe suite and a small React/JSDOM/TypeScript probe suite, reusing current fixtures and esbuild. Cover each of the 26 pack criteria with an ID, actual observation, evidence and PASS/FAIL/PARTIAL/BLOCKED status. Inject clock/provider/network failures; do not sleep for real deadlines or load-test production. Keep genuine provider email/reset-link reuse separate from local stub tests. Use lightweight browser reads for the live action route if shell networking remains unavailable. No subagents were requested.

Important code/coverage already inspected:

- `backend/app/tests/conftest.py`: isolated SQLite session and temporary storage fixtures, valid local anonymous cookies/CSRF. `backend/app/tests/test_accounts.py`: `accounts` fixture, `Provider`, `login`; real account routes with only identity provider stubbed. Covers expiry, revocation, cross-account private cases/files and stale tabs.
- `backend/app/api/endpoints/cases.py`: repeated create requests insert new cases; no evident idempotency key. Do not declare this a failed browser double-click check without actually distinguishing UI guards from API replay.
- `frontend/src/pages/Capture.tsx`: capture `inFlight` ref guards repeated analysis, whitespace validation and a 50,000-character paste limit. The save handler uses pending state. Source dates are validated as calendar dates, but connected uploads do not persist communication dates. Test actual behavior; do not infer future-date results only from source.
- `frontend/src/api/capture.ts`: recover/reconcile upload failures by hash; uncertain create responses block blind retries; retry can reuse saved case/evidence. Connected manual-only saving is unsupported. Most capture unit fixtures use demo mode: label them accurately.
- `backend/app/api/endpoints/evidence.py`: 10 MiB limit, MIME signature validation, atomic version claim, private storage and file hash. Repeated identical uploads appear to be accepted as separate records; execute a dedicated probe before assigning a verdict.
- `backend/app/ai/document_processor.py`: 50,000 text-character, 50 PDF-page and 12-megapixel limits. Backend timeout/unavailable/malformed-output coverage exists in `test_extractions.py` and `test_final_acceptance.py`.
- `backend/app/services/case_state.py`: computes overdue from active UTC deadlines, does not mutate active promises to fulfilled, uses optimistic compare-and-swap. A controlled clock can fix the reference to 15 November 2026 for the Part 3 scenarios.
- `backend/app/api/endpoints/extractions.py`: reviewed new/revision saves, preserved predecessor/evidence, stale-version and review replay checks. Reuse a validated deterministic candidate fixture rather than paying for AI again.
- `frontend/src/api/mapper.ts`, `frontend/src/lib/cases.ts`: current commitment totals and dashboard projections; compare them with API fixtures. `frontend/src/api/planning.ts` builds in-app activity and excludes resolved cases. Background notifications and connected deletion remain absent in this checked-out release: separate missing-feature findings from regressions.
- Backend complaint route in `cases.py` is deterministic, uses reviewed dates/amounts/evidence and asks for an update; it does not call an AI provider. `frontend/src/api/complaint-document.ts` says “I have not confirmed fulfilment” rather than automatically alleging failure. Execute the actual overdue/unverified scenario and review source citation/quote coverage.
- `frontend/src/state/Capture.tsx` retains unsaved inputs in React memory; `Auth.tsx` account gate can unmount routes on expiry. Test whether preservation survives reauthentication, not merely a network error.
- `frontend/checks/react-auth.test.mjs` demonstrates bundling real React components with JSDOM and narrowly stubbed boundaries. Existing reset tests verify length policy with stubbed provider; real reset issuance/use/reuse still needs external-provider evidence.

## Resume action

Do not repeat the already-passing baselines without a new reason. Implement the dedicated remaining-pack probes, execute them with isolated data, investigate observed failures without silently fixing product behavior, and finish `docs/EXTREME_TEST_REPORT.md` with all 26 scenario results, reproduction steps, severity, limits and prioritized fixes. Keep raw results reproducible. The user requested a test report, not an implementation of the earlier feature roadmap.
