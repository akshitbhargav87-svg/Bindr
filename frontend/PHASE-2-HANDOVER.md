# Phase 2 — app shell, overview and cases

Completed 14 Nov 2026. Stop for Tushar's review before Phase 3.

## Open

- http://127.0.0.1:5173/app — first-visit introduction, then Overview.
- Choose **Explore sample cases** to see the five required fixtures. **Start your workspace** opens the empty state.
- http://127.0.0.1:5173/app/cases — search company/promise and combine it with one clearable status filter. Query and filter live in the URL and survive navigation.
- The top-right **Demo workspace** control switches between sample, empty, offline and load-error states. It can show the introduction again. Those controls exist only in mock mode.
- Choose **Needs a date** with sample cases to inspect filter-empty; search an unmatched word to inspect no-results. Retry restores the sample view after a simulated failure. Native browser offline/online events are also handled.

## Works

- 232px desktop sidebar and four written mobile bottom tabs: Overview, Cases, Evidence, Settings. The active state uses Bindr's indigo edge. Top bar, labels, help links and live route titles are wired.
- Shared Nunito headings and Inter 16px body / 14px metadata; foundation colors, status colors, borders, buttons and brand come from the same tokens as the approved landing page. No new theme, fonts, photos, shadows or dependencies.
- Overview: unboxed summary strip, urgent cases, upcoming dates and confirmed resolutions. Four open cases, ₹5,798 awaiting, one overdue, one due today.
- Cases: search, filter counts, clearable selections, empty/no-result states, keyboard-accessible row links and responsive rows with visible amount/date/status.
- First visit, empty workspace, loading state, offline banner, load-error/retry, missing case and retained data during a lost connection.
- A minimal read-only case summary makes each list row useful. Full detail/timeline/outcomes remain Phase 4.
- Evidence, capture and settings routes resolve to honest read-only/checkpoint screens. No fake uploads, saves, outcome writes or preference toggles. Help contains the five status definitions.
- Only introduction/demo-view preferences use localStorage. Evidence and cases are not persisted in browser storage by this phase. Storage failures fall back to in-memory preferences.

## Architecture / contract

Components import the workspace service and UI models, never fixtures. HTTP mode uses only existing GET /cases and GET /cases/{id}, with at most four concurrent detail reads; no list-summary endpoint invented. Partial read failures do not present incomplete totals as complete. Cases with no reviewed commitments do not appear as tracked promises.

The mock adapter alone computes relative day status using MOCK_TODAY = 14 Nov 2026 and Asia/Kolkata. NovaMart's original 9 Nov and revised 12 Nov commitments and original evidence links are separate, so amounts are not doubled. Resolution takes precedence; a missing deadline gets Needs a date. The mapper uses backend status in live mode and does not infer overdue from the browser clock.

GAP: the API still lacks a reference date, timezone field, rich due-today status and aggregate list fields. Live mode preserves available server statuses; timezone follows the documented Asia/Kolkata integration assumption. Existing GAPS.md also applies. No backend was started/changed or tested end to end.

## Files

- Modified: src/App.tsx, src/main.tsx, src/styles.css, src/landing.css, src/api/{index,mapper,mock}.ts, README.md, GAPS.md.
- Added: src/api/workspace.ts; src/state/Workspace.tsx; src/lib/{cases,format}.ts; src/components/workspace/{WorkspaceLayout,WorkspaceStates,CaseList}.tsx; src/pages/{Overview,Cases,WorkspaceSupporting}.tsx; src/workspace.css; checks/workspace.test.mjs; this handover.
- Dependencies added: none. Fonts are the existing local packages. The lightweight checks use Node and Vite's installed esbuild dependency.
- Research screenshots were read from the existing archive; none were copied into the repository.

## Validation

- npm run build — passed; includes TypeScript checking and production bundle.
- npm run typecheck — passed.
- node --test checks/workspace.test.mjs — 5 passed: totals/resolved exclusion, preserved revision/evidence, missing-date/server-status boundary, search+status combination, snapshot isolation.
- git diff --check — no whitespace errors.
- Local /app, /app/cases and /app/help return HTTP 200 from the existing dev server. These are route response checks, not browser interaction tests.
- No long browser/screenshot loops. Desktop/mobile visual review remains with Tushar; browser rendering/keyboard/actual device interaction is not claimed verified in this environment.

## Next

Phase 3 implements capture, processing, editable extraction review and explicit confirmation with recovery paths. Full timeline, evidence viewing and case actions remain Phase 4. Preferences/agenda/inbox remain Phase 6. Stop here for review.

## Suggested manual commit

Suggested message: `feat(frontend): add Bindr workspace dashboard and case browsing`

In Command Prompt, after review:

```cmd
cd /d "C:\Users\Test\OneDrive\Documents\ChatGPT\PromiseKeeper - VIHAANX\bindr-app"
git branch --show-current
git add frontend/
git --no-pager diff --cached --stat
git commit -m "feat(frontend): add Bindr workspace dashboard and case browsing"
git push -u origin feature/frontend
```

The branch should be feature/frontend and every staged path should start frontend/. Stop if a command errors. No Git staging, commits, pushes, branch changes, PR actions or deployment were performed by the assistant. docs/ stays untracked and unstaged.
