# Phase 4 — the case, its history and its outcome

Completed 14 Nov 2026. Stop for user review before Phase 5.

## Review locally

Open http://127.0.0.1:5173/app/cases and choose a case. Use the top-right Demo workspace menu to select Sample cases if necessary.

- NovaMart: http://127.0.0.1:5173/app/cases/00000000-0000-4000-8000-000000000001 — compare the original 9 Nov and revised 12 Nov deadlines, exact quotations and separate originals.
- Record outcome: choose partial, record INR 1000 actually received, then inspect the remaining INR 3999, unchanged deadline, timeline and dashboard. Still waiting records a note only. Full receipt requires confirmation that every active promise was fulfilled.
- Add communication: paste a message or use the sample selector. Confirm case matching. Choose new versus revised promise, select its predecessor, explain a revision and confirm. The old terms/source links remain. Keep as evidence only leaves the promise untouched. Company claims fulfilment never resolves the case.
- Evidence: http://127.0.0.1:5173/app/evidence — search sources, open exact originals, inspect linked quotations and download. A drawer opens on desktop and fills the screen on mobile. Recovery preview: http://127.0.0.1:5173/app/evidence?missing=1.
- More actions on a case: edit company/title with a reason, archive/restore or delete. Deletion requires the complete case UUID and confirmation. Archive retains originals; http://127.0.0.1:5173/app/archived opens archived records.
- Orbit Store starts resolved. Reopen with a reason; its earlier confirmation remains in the history. Reopening explicitly makes the full promise outstanding again, with its original deadline.

Default mock changes, outcomes and original file bytes live in this tab only. Reload restores seed data and clears new records. No OCR/provider is connected. Newly uploaded image/PDF originals can be viewed/kept; local extraction reads UTF-8 text only.

## Implemented

- One existing Bindr design system: Nunito headings, Inter body/metadata, indigo, white/cool-grey/lilac surfaces, 1px borders and no shadows. Shared header/status/action patterns and mobile navigation remain consistent.
- Actual detail reads replace the Phase 2 summary route, including evidence-only cases. Loading, offline, read failure/retry and missing/deleted-case states are handled.
- Current amount, deadline and outcome summary; original/revised comparison; ordered vertical activity timeline. Canonical promises, quotations, source references, receipts, check-ins and management events remain distinct.
- Explicit revision review appends a successor, marks its predecessor superseded and preserves original terms/evidence. Multi-item reviews are atomic; one predecessor cannot branch into two accepted successors. Conflicting dates require a user choice and revision reason.
- Evidence library includes originals from tracked and evidence-only cases, including archived records. Downloads use authenticated contracted paths constructed from IDs, never externally supplied URLs. Safe previews support text, PNG/JPEG and PDF; HTML/SVG are not embedded. Blob URLs are revoked, stale responses ignored, and dialogs support native focus/Escape behavior.
- Seed messages are actual synthetic UTF-8 originals; source quotations are exact substrings and SHA-256 values match their bytes. Earlier PDF metadata placeholders are now text files, not fabricated PDFs.
- Partial monetary receipts must be positive and below outstanding; full balance uses full fulfilment. Non-monetary partial outcomes require a description. Partial outcomes keep reviewed totals and deadlines unchanged and can remain overdue. Workspace totals show remaining amounts, with written partial labels.
- Failed saves preserve entered fields. Version conflicts and uncertain requests block repeat submission until a fresh case is checked; reconciliation is reachable inside dialogs. An explicit re-analysis cannot recover an older draft for replaced evidence.
- No complaint drafting was added. No new dependency, backend change, automatic sending, Git mutation or deployment.

## Contract and limitations

HTTP supports case reads, evidence upload/download, extraction, new/revision review and full resolution with expected_version, cookies and CSRF. No live session/backend was started or verified end to end.

Partial/pending outcomes, reopen, edit, archive/restore, delete, communication-date metadata, claim labels and decision notes have no v1 endpoints. These remain local mock extensions with GAP comments; connected mode blocks unsupported actions or states which annotations are not stored. HTTP evidence-only updates retain uploaded originals and reject any extraction draft, without inventing note fields. Original/revised source links and confirmed terms are stored through the actual review contract.

Edit case details changes company/title with an audit reason. It does not overwrite reviewed amounts/deadlines or originals. Promise changes use Add communication and explicit revision review. There is no generic promise-correction endpoint.

Manual mock promises still have no AI extraction/quotation record; this remains the Phase 3 integration gap. Archive/delete changes are local session behavior, not a production deletion or storage guarantee. Evidence library reads are bounded-concurrency per-case reads for the small MVP, not an invented library endpoint. See GAPS.md.

## Files

- Added services/models: src/api/case-model.ts, case-service.ts, seed-evidence.ts.
- Added pages: src/pages/CaseDetail.tsx, CaseCommunication.tsx, EvidenceLibrary.tsx; case-detail.css, communication.css, record-library.css.
- Added components: src/components/workspace/EvidenceViewer.tsx, OutcomeDialog.tsx, CaseActionDialog.tsx with their own CSS files.
- Updated routing, workspace title, case rows/archive link, mapper, mock state/seed handling, HTTP original downloads and capture draft recovery. Updated README.md/GAPS.md and this handover.
- Added checks/case.test.mjs and one capture regression. Dependencies added: none. Shared API types/docs and backend were not changed; all writes stayed in frontend/. Research sheets were viewed in the read-only workspace and not copied into the repository.

## Validation

- npm run build: passed, including TypeScript and production bundle.
- npm run typecheck: passed.
- node --test checks/workspace.test.mjs checks/capture.test.mjs checks/case.test.mjs: 34 passed. Includes exact seed bytes/hashes/quotes, missing/cross-case sources, revision preservation, atomic/stale reviews, partial balances, claim handling, resolution/reopen history, archive/restore/delete, authenticated download routing, re-analysis recovery and same-day event order.
- Detail, communication, evidence and archive routes returned HTTP 200 from the existing dev server. These are response checks, not browser interaction tests.
- No screenshot/browser loop was run. Desktop/mobile visual review, actual-device keyboard behavior and real backend integration remain unverified.

## Suggested manual commit after review

Suggested message: `feat(frontend): add case timelines evidence and outcome workflows`

Run in Command Prompt; copy only the command lines:

```cmd
cd /d "C:\Users\Test\OneDrive\Documents\ChatGPT\PromiseKeeper - VIHAANX\bindr-app"
git branch --show-current
git add -- frontend/
git --no-pager diff --cached --stat
git commit -m "feat(frontend): add case timelines evidence and outcome workflows"
git push -u origin feature/frontend
git rev-parse HEAD
git ls-remote origin refs/heads/feature/frontend
git status -sb
```

The branch should be feature/frontend; every staged path should begin frontend/. Stop if any command errors. Local/remote hashes should match after push. docs/ stays untracked and unstaged. No staging, commits, pushes, branch/PR operations or deployment were performed by the assistant.

Next: Phase 5 complaint preparation, editable draft, review and supported copy/export, after review.
