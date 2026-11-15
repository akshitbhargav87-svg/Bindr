# Bindr remaining stress-test report

15 November 2026. Tested application: `codex/account-auth`, commit `888722d1456380d4c5a370d15f49b7b9ee0d0c16`. Product code/deployment unchanged. New test probes and report are local, not pushed commits.

## Result

**26 scenarios assessed: 16 pass within stated scope, 5 fail, 4 partial, 1 blocked.** The five failures include unsupported workflows and robustness gaps; they are not all regressions.

The saved baseline already had **124 backend + 81 frontend checks passing**. This resumed run added **18 backend probe executions + 6 React/projection executions**, all executing successfully. These harness successes mean observations were reproduced, including product failures; they do not mean all desired behavior passed. Part 1's ten AI stress cases were excluded per the user; Part 4 is only a priority list.

## Method

Real FastAPI endpoints, SQL state, temporary local evidence storage and document parsing were exercised with synthetic data. General probes use local signed sessions; account probes use Firebase-mode fixtures with the external identity provider stubbed. React forms/providers were mounted in JSDOM with controlled workspace/capture/provider boundaries. Deadline tests use a fixed server clock. No paid AI requests, production stress writes, emails, password changes or feature fixes were made.

SQLite cannot establish PostgreSQL concurrency behavior. Sequential stale-version probes are not two real browser tabs. JSDOM verifies state/rendering logic, not visual layout or real DevTools throttling. Provider-stub tests are not live Firebase credential tests. Local behavior is attributed to the tested commit; only the four explicitly recorded read-only observations below are live-service findings.

## Part 2 — Website/backend

| ID | Scenario | Verdict | Actual observation and boundary |
|---|---|---|---|
| P2-01 | Duplicate submission | **FAIL** | Identical create-case API requests both return 201 with distinct IDs. Same-turn double submit of actual React capture invokes preparation once, so that UI guard passes; API replay is not idempotent. Final review-button double-click was not separately tested. |
| P2-02 | Huge input | **PASS** | Actual paste form rejects 100,000 characters before preparation. Parser accepts 50,000 and rejects 100,000 with explicit size error. A 100 KB text file may be retained as evidence but cannot pass the parser. |
| P2-03 | Empty message | **PASS** | Spaces/newlines produce validation error before case preparation/upload. Actual React form exercised. |
| P2-04 | Duplicate evidence | **FAIL** | Same valid PNG bytes uploaded twice with current versions create two IDs sharing the same hash, with no response warning/deduplication indicator. Source inspection shows no connected content-deduplication step. |
| P2-05 | Oversized PDF | **PASS** | Actual greater-than-10-MiB upload returns 413 FILE_TOO_LARGE; no evidence row saved. |
| P2-06 | Corrupt PDF | **PASS** | PDF-signature bytes are retained; extraction then returns graceful 422 UNREADABLE_EVIDENCE with no commitment. Parse validation occurs during extraction. |
| P2-07 | Renamed .txt→.pdf | **PASS** | Actual bytes are detected and stored as text/plain despite declared application/pdf. Extension remains .pdf, a possible labeling issue, but the server does not trust it as PDF. |
| P2-08 | Communication date 2099 | **FAIL** | Actual React form accepts 2099-01-01 with no future-date warning. Connected upload does not send/persist that field (source inspection), so there is no persisted communication-date policy. |
| P2-09 | Race/stale tabs | **PARTIAL** | Two writes with expected version 1 return 201 then 409; one evidence row. Sequential stale-state simulation, not simultaneous PostgreSQL or real two-tab UI. |
| P2-10 | Slow AI/retry | **PARTIAL** | Deferred React preparation shows loading and suppresses repeat submit. Injected timeout returns 504; original/version survive; retry succeeds without another original. No real timeout duration or DevTools throttling exercised. |
| P2-11 | Network/service failure | **PASS** | Injected React network rejection restores recoverable form with exact pasted text. Separate backend 503/retry probe preserves original/version and permits retry without re-upload. No physical internet disconnect. |
| P2-12 | Expiry/draft preservation | **FAIL** | Expired SQL account session correctly returns 401; fresh stub login restores saved-case access. Rekeying actual CaptureProvider resets unsaved text; App's account/status-keyed ancestor remounts that subtree during auth transitions. State-lifecycle reproduction, not live Firebase reauthentication. |
| P2-13 | Cross-account access | **PASS** | Owner reads case/original; a second distinct identity receives 404 for both. Real API/SQL authorization with stubbed external identities. |
| P2-14 | Bare /auth/action | **PASS** | Live path returns 200 HTML SPA shell. Actual React Auth page with configured provider stub displays unsupported-link state instead of generic 404. HTTP shell alone does not establish live hydration. |
| P2-15 | Real password reset/reuse | **BLOCKED** | No dedicated controlled inbox/reset link available in this run. Stubbed reset-policy tests do not prove issuance, delivery, first use or replay rejection. Requires a controlled test account and user-operated password change. |
| P2-16 | Malformed AI response | **PASS** | Incomplete candidate returns 502 AI_INVALID_OUTPUT; no extraction/commitment rows and unchanged case version. |

## Part 3 — Deadline/accountability

| ID | Scenario | Verdict | Actual observation and boundary |
|---|---|---|---|
| P3-01 | Due tomorrow | **PASS** | Fixed 15 Nov clock: 16 Nov deadline is open, not overdue. |
| P3-02 | Overdue, outcome unknown | **PASS** | 12 Nov deadline projects overdue; obligation stays active without invented receipt/nonfulfillment event. |
| P3-03 | Early fulfillment/reminders | **PARTIAL** | Early user resolution succeeds and marks commitments fulfilled. No background reminder delivery exists to cancel/test. Existing in-app activity checks exclude resolved cases. |
| P3-04 | Revised deadline | **PASS** | Controlled reviewed 17→22 Nov revision retains both rows/dates, predecessor and evidence. Same source reused to isolate persistence; semantic AI revision detection is outside this test. |
| P3-05 | Multiple deadlines | **PARTIAL** | Separate dates retained; a past active obligation makes the case overdue. Real frontend mapper aggregates amounts and displays earliest date. Individual-obligation visual status clarity not checked in a real browser. |
| P3-06 | Deleted case | **FAIL** | DELETE case returns 405 and record remains. Connected deletion and background reminder cancellation are unsupported. |
| P3-07 | PST/IST midnight | **PASS** | Not overdue at exact IST-midnight UTC equivalent; overdue one second later. Same calendar midnight at -08:00 remains upcoming. Numeric offsets used, not ambiguous abbreviation extraction. |
| P3-08 | Complaint facts | **PASS** | Actual follow-up generation includes correct company, INR 4999.00, original/revised dates, evidence ID and filename. History retained. Does not independently authenticate company evidence. |
| P3-09 | No unsupported breach | **PASS** | Controlled overdue case without outcome generates update request, without alleging breach, failed payment or nonreceipt. User-authored remedy remains user text, not independently verified facts. |
| P3-10 | Dashboard totals | **PASS** | Real mapper/summary fixture: 2 open tracked cases, INR 400 outstanding, 1 overdue. Superseded INR 100, resolved INR 900 and review-only record excluded. Not a live SQL-to-browser reconciliation. |

## Fix priorities and reproduction

1. **High: unsaved text lost on account transition (P2-12).** Enter a message, then trigger session expiry/auth-status change. Actual provider rekey resets capture. Add account-safe draft recovery and a reauthentication regression test; never expose one account's unsaved text to another account.
2. **Medium: case-create replay (P2-01).** POST identical valid title/company twice: two 201s. Add account/operation-scoped idempotency and uncertain-response reconciliation. Keep UI click guards. Identical titles alone must not merge intentional separate cases.
3. **Medium: duplicate originals (P2-04).** Upload identical PNG bytes with versions 1 then 2: two IDs and equal hashes. Add same-case warning or an explicit deduplication policy.
4. **Medium: communication-date policy/persistence (P2-08).** Submit 2099-01-01: accepted without warning, then omitted from connected upload. Persist date/provenance and define warning/confirmation policy. Future communication dates and legitimate future deadlines are different concepts; blanket rejection is a proposed product criterion, not an established universal rule.
5. **Missing feature: delete/reminders (P3-06/P3-03).** Implement authenticated retention/cleanup and durable notifications before advertising them. This is an absent workflow, not a demonstrated broken existing deletion job.

## Live read-only checks

Using the existing live hostname: `/health` returned 200 healthy; `/api/v1/auth/config` returned 200, firebase/configured true; `/auth/action` returned 200 HTML; unauthenticated `/api/v1/cases` returned 401. The earlier restricted-shell DNS failures were environmental; resumed reads with network access succeeded. No deployment SHA was re-read, so these are limited endpoint observations, not proof that every local test matches the current live revision.

## Reproduction and raw evidence

Sources: `backend/app/tests/test_extreme_pack.py` and `frontend/checks/extreme-pack.test.mjs`. The React probe is run explicitly, not added to default npm checks. Use installed dependencies and the existing virtual environment. Set process-local `ENVIRONMENT=development`, `AUTH_PROVIDER=anonymous`, `AI_PROVIDER=mock`, `DATABASE_URL=sqlite:///./storage/extreme-testing-2026-11-15/probes.db`, `OCR_MODEL_DIR` to the existing model directory and `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. Never point these mutating probes at production SQL/storage.

```text
.venv\Scripts\python.exe -m pytest backend/app/tests/test_extreme_pack.py -q --junitxml=storage/extreme-testing-2026-11-15/scenario-backend.xml
cd frontend
node --test checks/extreme-pack.test.mjs
```

Clear only the two generated JSONL files before a new run; the probes append observations. Final clean run: backend **18/18, 2.42s**; React/projection **6/6, 2.73s**. Harness setup mistakes (Windows oversized parameter ID, parser method signature, esbuild/context wiring) were corrected before this run and not counted as app defects. Probe execution success intentionally includes assertions confirming current product shortcomings.

Raw evidence in `storage/extreme-testing-2026-11-15/`: `scenario-backend.log`, `scenario-backend.xml`, `scenario-backend.jsonl`, `scenario-frontend.log`, `scenario-frontend.jsonl`, `live-http-resumed.json`, plus saved baseline logs/XML. Final JSONL files were cleared before the clean run. Source pack remains in `docs/EXTREME_TEST_PACK.md`.

## Remaining acceptance

Use a dedicated test inbox/account to request reset, use its link, personally set the password, then reopen the same link and confirm rejection. Do not change a real user's credentials just to finish a report. PostgreSQL simultaneous races, two actual tabs, live reauthentication with draft recovery, real notification cancellation and cross-device visual reconciliation remain explicit limits of partial results. No fixes, cloud changes, merges or deployments were made during this request.
