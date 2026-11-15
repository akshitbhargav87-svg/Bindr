# Post-archive Bindr integration retest — 15 November 2026

**Scope:** Fresh tests against the owner-uploaded `codex/qa-integration` Git archive in an isolated environment. Historical reports remain unchanged. This is **not** a production release or main-branch merge approval.

## Source fixes in this review

1. `tests/contracts/platform/test_fixtures.py`: the frozen QA fixture manifest records the original CRLF (Windows-style) bytes, while Linux checkout normalizes the Markdown file to LF. The test now hashes a canonical CRLF representation on both platforms, rejects unsupported bare carriage returns and still detects changed canonical text. **Neither the QA pack nor the manifest SHA was modified.**
2. `frontend/src/components/workspace/WorkspaceStates.tsx` and `frontend/src/pages/PlatformWorkspace.tsx`: the optional add-promise destination now points v2 workspace buttons and empty-state calls to the v2 capture tool, not the legacy capture route. Standard routes and the original UI still default to `/app/upload`.
3. `frontend/src/pages/IntelligenceCapture.tsx`: v2 case titles follow the original optional-title behavior, using a deterministic bounded fallback. The provided title remains respected.

## Fresh results in this limited environment

| Test | Observed result | Limits |
|---|---|---|
| Platform canonical fixture tests | **4 passed** | Includes LF/CRLF portability and content-tamper regression. |
| Platform contracts without disposable PostgreSQL | **4 passed, 5 skipped** | Real concurrent PostgreSQL transaction checks require `BINDR_TEST_DATABASE_URL`. |
| Intelligence contract/import/provider/relations tests | **41 passed** | Controlled local providers; not real Meta acceptance. |
| Previous missing-engine and RFC3161 tests | **2 passed** | Local OpenSSL; not independent external timestamp validation. |
| All available backend and AI tests except unavailable cloud SDK collection | **282 passed, 4 failed, 3 subtests passed** (before the portable fixture edit) | Failures here: missing `firebase_admin`; missing real RapidOCR processor / available OCR route; one fallback OCR result misread “refund” as “tefund”; one OCR-derived deadline was not recognized. These are environment-specific and do not establish the release CI result. |
| TypeScript syntax transpilation for changed files | **3 passed** | Global TypeScript parser; no dependency/type resolution. |
| Full frontend suite and production build | **Not run** | Project `node_modules` unavailable; network package installation disabled in this execution environment. |
| Live auth/Meta/browser/Cloud SQL/backup/worker | **Not run** | Requires real controlled services and release authorization. |

The source ZIP is an archive of tracked files only: it does not include `.git` history, production secrets, node dependencies or a working cloud environment. GitHub CI after the branch update is the authoritative independent Linux/Node/PostgreSQL check. A previously observed PR #5 CI run failed specifically on the raw fixture SHA mismatch; other CI steps did not run after that failure.

## Completion gate

This patch does **not** claim that the default original v1 screens are fully connected to the v2 APIs. Until that integration, source-tied real AI cases, production browser privacy, scheduled worker and backup restoration are proven, keep PR #5 in review and do not deploy or automatically merge into `main`.
