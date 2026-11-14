> Historical branch handover. The combined release supersedes session, route, OCR and acceptance-status notes below. See the [current release audit](../docs/RELEASE_AUDIT.md).

# Bindr — frontend integration handover

14 Nov 2026. Frontend Phases 1–6 are implemented. Phase 7's frontend wiring, contract checks, connected build and handover are complete. Testing against the real FastAPI/backend/AI is still pending: `http://127.0.0.1:8000/api/v1/cases` refused the connection during this pass. No backend source is present in this frontend clone; no backend was started, modified or substituted as a production service.

## Contract audit

The local docs were compared with feature/integration on GitHub on 14 Nov 2026. Text matches after ignoring final newline differences. No routes, request keys or response enums were invented. References: [API contract](https://github.com/akshitbhargav87-svg/Bindr/blob/feature/integration/docs/API_CONTRACT.md), [AI contract](https://github.com/akshitbhargav87-svg/Bindr/blob/feature/integration/docs/AI_CONTRACT.md), [architecture](https://github.com/akshitbhargav87-svg/Bindr/blob/feature/integration/docs/ARCHITECTURE.md), [environment](https://github.com/akshitbhargav87-svg/Bindr/blob/feature/integration/docs/ENVIRONMENT.md).

| Flow | Existing HTTP route | Frontend behavior |
|---|---|---|
| Create/list/detail | POST /cases; GET /cases; GET /cases/{id} | Typed adapter, cookie credentials, explicit error states; no fixture fallback in HTTP mode |
| Original evidence | POST /cases/{id}/evidence; GET /cases/{id}/evidence/{evidenceId}/content | One multipart file + expected_version; original raw bytes; constructed private route, not supplied external URL |
| Extract/review | POST /cases/{id}/extractions; POST /cases/{id}/extractions/{draftId}/review | Pending suggestions only; explicit new/revision confirmation; expected_version, preserved originals and predecessor links |
| Fulfilment | POST /cases/{id}/resolve | Full user-confirmed fulfilment of every current promise |
| Complaint | POST /cases/{id}/complaint-draft | Only expected_version/requested_remedy; editable preview, version checks, explicit reviewed copy |
| Agenda/activity/evidence index | Existing GET list/detail projections | Bounded-concurrency reads; no invented aggregate, notification or inbox endpoint |

HTTP success shapes are checked at the adapter boundary, including core types, money/date fields, case membership and positive versions. An invalid/unreadable successful mutation response is uncertain and blocks blind retry. Non-JSON auth errors stay typed; malformed CSRF tokens fail before transport. Reads use no-store. There are no automatic mutation retries. These guards supplement backend validation; they do not replace ownership checks, database constraints or provider validation.

## What was tested

- 55 Node checks passed across workspace, capture, case, complaint, planning/preferences and HTTP transport suites.
- A temporary loopback contract server ran the actual HTTP adapter through create → upload → extract → confirm → revised communication → revision review → complaint preview → original download → resolve. It checked multipart fields, cookie/CSRF transport, expected_version, stale-write rejection and source/history preservation. It closed at test completion.
- The test server used deterministic local domain fixtures. It was not FastAPI, PostgreSQL, production auth, a real private storage implementation or a real AI provider. Browser cookie policy/CORS, real authorization and live provider behavior remain unverified.
- Demo production build: npm run build → dist/. Connected production build: npm run build:http → dist-http/. Both passed; connected build leaves the default demo output/config unchanged. Both generated folders are ignored by Git.
- Agenda, activity, settings and help routes returned HTTP 200 from the existing dev server. This verifies route responses, not rendered interactions. No screenshot/browser-automation loop or actual-device certification was performed.

## Backend-team prerequisites for live testing

1. Start the actual API at port 8000 with its own configured database, private evidence storage and deterministic stub provider. Frontend cannot supply those commands without the backend implementation.
2. Supply the agreed authenticated session/bootstrap outside the domain API. Frontend sends credentials and echoes pk_csrf; it contains no test user, login token or backend secret.
3. Match browser/API hostnames. Use localhost for both, or 127.0.0.1 for both. Mixing them prevents SameSite=Lax cookies from working as expected. Set backend FRONTEND_ORIGIN to the exact frontend origin, including port; allow credentials and verify Origin/CSRF.
4. Use the backend stub for the first pass. A live provider/key/model and permission to send selected evidence text are backend-team decisions; keys never belong in VITE variables.

## Exact connected-frontend commands

After those prerequisites, open a fresh Command Prompt. This starts a second frontend on port 5174 without changing files or stopping the current demo:

```cmd
cd /d "C:\Users\Test\OneDrive\Documents\ChatGPT\PromiseKeeper - VIHAANX\bindr-app\frontend"
set "VITE_USE_MOCK=false"
set "VITE_API_URL=http://localhost:8000"
npm run dev -- --port 5174
```

Open http://localhost:5174/app. Backend FRONTEND_ORIGIN must be http://localhost:5174 for this run, and its session cookies must be issued for localhost. If the backend uses 127.0.0.1 instead, use that hostname in both VITE_API_URL and browser URL and configure the matching origin. Do not paste formatting markers as commands. Stop this extra dev server with Ctrl+C when finished.

For an existing production build, configure the same public variables at build time. `VITE_USE_MOCK=false` selects HTTP; VITE_API_URL accepts the API origin or an explicit /api/v1 base, including same-origin /api/v1. Session setup still belongs to the backend.

## Live verification once the backend is available

Use a synthetic order/message. Confirm no commitment exists before review; inspect the exact original; accept a new promise, then a revision preserving both dates and sources; verify stale writes fail without duplicates; generate/edit/review/copy the factual complaint; confirm full receipt and ensure only current promises become fulfilled. Also exercise 401/403, inaccessible case/source 404, unreadable text/PDF, provider timeout and lost-response reconciliation. Integration lead should separately verify private download authorization, original byte hashes, CSRF/Origin checks, database transactions and storage retention.

Do not call unsupported endpoints to simulate product parity. In HTTP mode screenshot OCR, manual-only saving, partial/pending outcomes, reopen/edit/archive/delete and extra timeline annotations remain blocked or clearly limited. Calendar/status enrichment, persistent saved drafts and notification channels require contract changes; see GAPS.md.

## Static hosting

Render Static Site: root directory frontend; build npm ci && npm run build; publish dist. Set public VITE_USE_MOCK=false and VITE_API_URL appropriately for a connected deployment. Configure an explicit rewrite `/*` → `/index.html` with action Rewrite for BrowserRouter deep links. public/_redirects is present but does not replace Render's dashboard rewrite. No deployment was performed.

No Git staging, commits, pushes, branch/PR operations, backend edits or messages to teammates were performed. Share this file and GAPS.md manually with the backend/AI/integration owners.
