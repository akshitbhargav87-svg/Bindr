# Phase 5 — complaint preparation, editing and export review

Completed 14 Nov 2026. Stop for user review before Phase 6.

## Review locally

Open http://127.0.0.1:5173/app/cases/00000000-0000-4000-8000-000000000001/complaint or use Prepare complaint on an unresolved case.

1. Facts: inspect confirmed promises and sources, open an original, and enter the requested resolution. Selecting a revision retains its predecessor chain and original sources. Removing an earlier promise removes its dependent revisions from the selection.
2. Prepare my draft: the local adapter returns factual text; connected mode uses the contracted backend endpoint. Original/revised dates and sources remain distinct. Confirmed partial receipts are reflected accurately in local drafts.
3. Draft: edit subject/body and add your name. Save draft stores an explicit copy for this tab. Change selected facts preserves the current wording until you explicitly replace it. Restore saved version asks before discarding unsaved changes.
4. Review: read the white document preview. Return to editing without losing text.
5. Export: choose promise-history and evidence-index appendices. Review personal details and confirm the contents before preparing the text. Original evidence files are never automatically attached.
6. Prepared: copy text or download .txt. Clipboard denial exposes selectable prepared text instead of falsely claiming success. No message is sent or filed.

Saved drafts: http://127.0.0.1:5173/app/drafts, also linked in the desktop sidebar and complaint header. Draft content persists through app/public-page navigation until reload. Drafts are in memory, not localStorage or server persistence. Copy/download to retain a file. Reload warns before losing work. One saved version per case is supported; later explicit saves replace it.

Failure recovery: expand Try failure recovery on the facts screen and make the next preparation fail once. Remedy and selections remain available; retry or start from a factual template. Templates intentionally contain placeholders for the user to complete.

## Implemented

- Facts → Draft → Review → Export states on one case route. Shared Nunito/Inter typography, indigo/cool-grey/white surfaces, flat borders, a 700px maximum document width and responsive source sidebar. Original files use the existing accessible viewer.
- Selected confirmed facts, predecessor/source preservation, requested remedy, processing, editable text, preview, local saved copy/restoration and empty saved-drafts state.
- Source citations use readable E-01/E-02 references tied to actual case evidence. Draft text and optional exported history retain original/revised deadlines. Evidence indexes list filenames and added dates; they do not claim to contain original attachments.
- The reviewed body, including its whitespace and edits, is used for export. Export confirmation resets after edits/options change. All generated source IDs are checked against the case before displaying a result.
- Fresh case/version checks after generation and before preparing/copying/downloading. Stale/closed/archived/deleted cases block inappropriate generation/export. Reload preserves wording and requested remedy while asking for renewed fact selection/replacement.
- Local mock partial receipts show the remaining amount without changing the reviewed total. Company claims do not become confirmed receipts. No legal assertions, policies or independently verified payments are invented by the local template.
- Separate draft-generation and draft-snapshot selections prevent a changed setup form from silently altering an already prepared document's history. History appendices include their original source references even if a provider's returned draft uses only a subset.
- Deleting a local case clears its working/saved drafts; late async updates cannot restore them. No full document text is persisted to browser storage.
- No new dependency, external asset, backend change, Git mutation, automatic sending or deployment. Phase 6 was not started.

## Contract and limitations

HTTP POST /cases/{id}/complaint-draft sends exactly expected_version and requested_remedy with existing cookie/CSRF handling. Its response uses subject/body/evidence_ids and case_version; the preview does not increment case version. Unknown sources, invalid lengths and stale snapshots are rejected. There is no automatic POST retry. Real backend/session/AI operation remains unverified end to end.

The backend accepts no selected facts, selected evidence or tone fields. Connected mode therefore keeps the full reviewed record selected and lets the user edit the returned text. Local mock selection is explicitly isolated behind its adapter extension. There is no PDF/export-package or saved-draft endpoint. .txt downloading and tab-local draft storage are frontend extensions with GAP comments; the manual fallback is a local editable template. Original-file sharing remains a separate user action. See GAPS.md.

Generated bodies remain bounded to 10,000 characters and subjects to 200. Very large local histories can exceed the draft limit; use the concise manual template or reduce selected independent facts. Exported history is plain text and can be longer than the editable body. Calendar/status logic remains in the existing adapters; no browser-clock overdue logic was added.

## Files and checks

- Added src/api/complaint-model.ts, complaint-document.ts, complaint.ts; src/state/Complaints.tsx; src/pages/Complaint.tsx; src/complaint.css; checks/complaint.test.mjs.
- Updated src/App.tsx, src/api/mock-mutations.ts, src/components/workspace/WorkspaceLayout.tsx, src/pages/CaseDetail.tsx and src/case-detail.css for routes, navigation, case action, mock drafting and deletion cleanup. Updated README.md/GAPS.md and this handover. All changes are inside frontend/; shared docs/backend were untouched.
- npm run typecheck: passed.
- npm run build: passed, including TypeScript and production bundle.
- node --test checks/workspace.test.mjs checks/capture.test.mjs checks/case.test.mjs checks/complaint.test.mjs: 46 passed. Twelve complaint checks cover history/quotes, receipt balances, invalid selections, manual recovery, stale/closed/archive guards, exact edited exports, confirmation, source completeness, response validation and exact HTTP transport with no sending endpoint.
- Complaint and saved-draft routes respond from the existing dev server. Route checks do not verify actual browser interactions. Clipboard permission, native download/device behavior, keyboard/device rendering and real backend integration remain for review; no long browser/screenshot loop was performed.

## Suggested manual commit after review

Suggested message: `feat(frontend): add editable complaint drafts and reviewed text export`

From a fresh Command Prompt, copy only these command lines:

```cmd
cd /d "C:\Users\Test\OneDrive\Documents\ChatGPT\PromiseKeeper - VIHAANX\bindr-app"
git branch --show-current
git add -- frontend/
git --no-pager diff --cached --stat
git commit -m "feat(frontend): add editable complaint drafts and reviewed text export"
git push -u origin feature/frontend
git rev-parse HEAD
git ls-remote origin refs/heads/feature/frontend
git status -sb
```

Branch should be feature/frontend; every staged path should begin frontend/. Stop if any command errors. The local and remote hashes should match after pushing. docs/ stays untracked/unstaged. Do not paste the formatting markers around the commands. The assistant performed no staging, commit, push, branch, PR or deployment actions.

Next: Phase 6 agenda/settings/mobile/accessibility polish, after review.
