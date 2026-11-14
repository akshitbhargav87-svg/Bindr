# Phase 3 — capture, review and confirmation

Completed 14 Nov 2026. Stop for review before Phase 4.

## Open and review

Open http://127.0.0.1:5173/app/upload on the existing dev server.

1. Expand **Try a sample communication**, choose **Clear refund promise**, then **Use this sample**.
2. Choose **Review the promise**. Compare the source with editable company, promise type, description, INR amount and confirmed date.
3. Check the confirmation box, then **Confirm & track**. The new record appears in Cases and Overview, including from an empty workspace.
4. Try the other samples: several promises, vague or ambiguous date, no promise, duplicate suggestion, extraction unavailable, and one failed save. Reviewed values remain available for retry.
5. Upload a UTF-8 text file to extract its actual text. Upload an image/PDF to preview the original and enter terms manually. The default adapter does not perform OCR or parse PDF text.

The active review is at `/app/review`. Files and edited fields survive navigation within the app. Closing/reloading the tab warns about unsaved input; mock records and original bytes are session-only and do not survive reload. An old review URL cannot restore them.

## Implemented

- Shared Nunito/Inter typography, existing indigo/cool-grey/lilac tokens, 1px borders, flat surfaces and consistent buttons. Desktop source/review split is 45/55; narrower layouts switch between Fields and Source without unmounting the form.
- Drag/drop or file chooser, upload queue, per-file communication date, replace/remove/paste alternatives, empty/type/10 MiB checks, and up to ten files. Pasted text is retained as an original UTF-8 file; text is not rewritten.
- Original text, image and native browser PDF previews with linked supporting quotations. New mock files retain original bytes in memory. Object URLs are revoked when a source changes or unmounts.
- Adapter-owned extraction creates pending suggestions only. Fields remain editable; multiple suggestions can be deselected independently. Confidence scores are never shown. A tracked commitment is created only after the user's confirmation.
- Mock relative dates count from the communication date, with Monday–Friday business days, no holiday exclusion, and Asia/Kolkata date-only deadlines. Ranges show their window and use its final day. Vague/ambiguous dates stay unset. Explicit extracted times are preserved until their calendar date changes.
- No-promise flow can retain evidence without adding a tracked commitment. Manual entry does not invent an extracted quotation. Duplicate suggestions require explicit separation and never merge cases.
- Processing, offline blocking, extraction/manual fallback, failed save retry, version conflict and uncertain-request recovery. Original uploads are reused on retry; a lost upload response is reconciled by filename and SHA-256. A lost create response cannot be safely retried without backend reconciliation.
- No new dependency, auth UI, external AI call or backend change. No complaints are sent or filed.

## Contract boundary

HTTP uses only the supplied case create, evidence upload, extraction and extraction-review contracts, including expected_version, cookies and CSRF. There is no automatic mutation retry. Real backend operation still requires session bootstrap and integration testing.

HTTP accepts UTF-8 text and text-layer PDF only; screenshots are not advertised as supported there. Manual-only saving, communication-date upload metadata, company/title edits after creation and duplicate detection have no API contract. Those features are local mock extensions; unsupported HTTP actions are blocked or explained. See GAPS.md. Mock manual commitments have no AI extraction record; production needs a manual-origin contract. Source browsing for seed fixtures and full original/revised case timelines remain Phase 4.

## Files

- Capture models, validation and service: src/api/capture-model.ts, capture-types.ts, capture-validation.ts, capture.ts.
- Mock behavior: src/api/mock-extraction.ts, mock-mutations.ts, mock.ts; mapper.ts marks seed fixtures for empty-workspace filtering.
- UI/state: src/pages/Capture.tsx, src/state/Capture.tsx, src/components/workspace/CaptureSource.tsx, src/capture.css.
- Wiring: src/App.tsx, main.tsx, state/Workspace.tsx, components/workspace/WorkspaceLayout.tsx, pages/WorkspaceSupporting.tsx.
- Checks: checks/capture.test.mjs; existing checks/workspace.test.mjs retained. README.md and GAPS.md updated.

## Validation

- npm run build: passed, including TypeScript and production bundle.
- Node checks: 19 passed across workspace and capture. Covers confirmation gating, original bytes, dates/times, selection, duplicates, manual fallback, retained evidence, save failure, version conflicts, upload retry/reconciliation and uncertain create blocking.
- `/app/upload` and `/app/review`: HTTP 200 from the existing local dev server. These checks verify route responses, not browser interactions.
- Desktop/mobile rendering and keyboard/device interaction are for user review; no browser screenshot loop or live AI/backend end-to-end check is claimed.

## Suggested manual commit after review

Run in Command Prompt:

```cmd
cd /d "C:\Users\Test\OneDrive\Documents\ChatGPT\PromiseKeeper - VIHAANX\bindr-app"
git branch --show-current
git add -- frontend/
git --no-pager diff --cached --stat
git commit -m "feat(frontend): add evidence capture and promise confirmation"
git push -u origin feature/frontend
git rev-parse HEAD
git ls-remote origin refs/heads/feature/frontend
git status -sb
```

The branch must be feature/frontend and staged paths must start frontend/. Stop if a command errors. The two hashes should match after pushing. No Git staging, commits, branch changes, pushes, PR actions or deployment were performed by the assistant. docs/ remains untouched.

Next: Phase 4 case detail, source-linked original/revised timeline and supported outcome actions, after this review.
