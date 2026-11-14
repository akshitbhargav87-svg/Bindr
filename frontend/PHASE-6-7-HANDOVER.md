# Phases 6 and 7 — planning, preferences, polish and integration

14 Nov 2026. Phase 6 is implemented. Phase 7 frontend wiring/checks/handover are complete; real backend end-to-end verification remains pending because localhost:8000 refused connection. See INTEGRATION-HANDOVER.md for the exact boundary and next steps.

## Review

- http://127.0.0.1:5173/app/agenda — overdue/due-today/confirmed-date/undated groups, searchable cases, original status labels. Resolved/archived cases are excluded. No browser-clock deadline inference is used.
- http://127.0.0.1:5173/app/activity — activity from actual case records plus authoritative deadline prompts. All/unread views, mark read/mark all read, case links and preference-aware categories. Read markers are local to this tab, not a server inbox.
- http://127.0.0.1:5173/app/settings — fixed Asia/Kolkata/calendar assumptions, real browser-local controls for in-app deadline prompts and case updates, and factual retention information. Turn prompts off and inspect Overview/Activity; case history and deadlines stay intact.
- http://127.0.0.1:5173/app/help — status definitions plus capture/calendar/revision/claim/complaint/privacy guidance. Native disclosure controls work without custom keyboard logic.
- Narrow the browser: four main bottom tabs remain Overview/Cases/Evidence/Settings; a separate short navigation row exposes Deadlines/Activity/Drafts. Sidebar navigation covers the same views on desktop.

## Changes

- Agenda and activity are read projections of existing data. Activity preferences have visible effects; there is no push subscription, email delivery, scheduler or background notification claim. Browser-storage failures apply preferences in memory with a clear notice. Only two booleans and a schema version are stored; case content/read-marker IDs are not persisted there.
- New views use the same Nunito headings, Inter 16px body/14px metadata, indigo, white/cool-grey/lilac surfaces, borders and flat rows. No new fonts, theme, imagery dependencies or packages.
- Mobile navigation, small-width summary stacking, long filename/reference wrapping, safe-area padding, smaller-height sidebar scrolling, visible focus, route-to-main focus, reduced-motion page scrolling, forced-color switch/status borders and help disclosures were added or refined.
- Capture state now survives navigation between the workspace and public landing page within the same app session. Complaint sessions already did so. Reload warnings still protect local work.
- API response guards, typed non-JSON errors, safe CSRF decoding, no-store reads and uncertain-success handling were added. Existing supported HTTP flows remain exact to the shared contract, without automatic write retries or fixture fallback.
- A real local HTTP transport check was added using a temporary deterministic test server. It exercises the actual adapter through the core demo path and closes the server afterward. This does not certify the unavailable real backend.
- Added npm run check and npm run build:http. The latter builds connected mode into ignored dist-http, preserving the existing default demo config/output. GitHub contract text was read and compared with the local reference copies; no request/response rules differ.

## Files

Added src/api/{planning,preferences,protocol}.ts; src/state/Preferences.tsx; src/pages/{Planning,Settings}.tsx; src/{planning,polish}.css; checks/{planning.test,http-flow.test,build-http}.mjs; INTEGRATION-HANDOVER.md; this handover. Updated App.tsx, main.tsx, styles.css, Overview.tsx, WorkspaceSupporting.tsx, WorkspaceLayout.tsx, http.ts, package.json, .env.example, .gitignore, README.md and GAPS.md. Dependencies added: none. All writes stayed inside frontend/; backend/shared docs/root files were untouched.

## Validation and limits

- npm run typecheck: passed.
- npm run check: 55 passed. Includes previous 46 plus agenda grouping/no clock inference, activity preference/category/stable-ID behavior, archived exclusion, corrupt/blocked preference storage, full loopback HTTP journey, malformed successful response recovery, auth/token errors and cross-case response rejection.
- npm run build: passed, output dist.
- npm run build:http: passed, output dist-http with VITE_USE_MOCK=false.
- New routes returned HTTP 200 from the existing local dev server; no long browser/screenshot loop was run. Actual device rendering, native dialog interactions, clipboard/download permissions and a browser accessibility audit remain user-review items.
- Live backend check: http://127.0.0.1:8000/api/v1/cases refused connection. Auth bootstrap, browser CORS/cookie behavior, FastAPI/database/private storage and real AI end-to-end are unverified. This is the outstanding Phase 7 dependency, not a passed integration claim.

## Suggested manual commit after review

Suggested message: `feat(frontend): finish agenda preferences and API integration checks`

Copy only the command lines into a fresh Command Prompt:

```cmd
cd /d "C:\Users\Test\OneDrive\Documents\ChatGPT\PromiseKeeper - VIHAANX\bindr-app"
git branch --show-current
git add -- frontend/
git --no-pager diff --cached --stat
git commit -m "feat(frontend): finish agenda preferences and API integration checks"
git push -u origin feature/frontend
git rev-parse HEAD
git ls-remote origin refs/heads/feature/frontend
git status -sb
```

Branch should be feature/frontend, every staged path should start frontend/, and local/remote hashes should match after push. Stop if a command errors. Do not paste the formatting markers. docs/ remains untracked and unstaged. No staging, commit, push, branch/PR action, backend change, external message or deployment was performed by the assistant.

The remaining step is the real backend/session run described in INTEGRATION-HANDOVER.md, followed by user visual review and any resulting fixes.
