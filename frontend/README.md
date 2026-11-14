# Bindr frontend

Phase 5 is implemented: each unresolved case can prepare a complaint from its reviewed record, edit the text, preview, review the export, and copy/download UTF-8 text. `/app/drafts` keeps explicitly saved versions in this tab only. Generation failures preserve selections and offer a local factual template. Exports recheck the case version and require confirmation. See PHASE-5-HANDOVER.md for review steps and backend limits. Earlier phase sections below are historical where superseded; Phase 6 has not started.

Phase 4 is implemented: case detail and preserved revision timeline, original-evidence viewer/library, case communication review, outcomes and local lifecycle actions. Start at `/app/cases` or open `/app/evidence`; archived records are at `/app/archived`. Full resolution, source downloads and revision reviews use the supplied HTTP contract. Extended outcomes and case management remain mock-only. See PHASE-4-HANDOVER.md for review steps, validation and limitations. Phase 5 has not started.

Phase 3: `/app/upload` accepts source files or pasted messages; `/app/review` opens editable, source-linked fields with explicit confirmation. Default mock extraction reads text locally; screenshots/PDFs support preview and manual entry, without OCR. New records and their original files remain in this tab until reload. See PHASE-3-HANDOVER.md for that phase's review steps and integration gaps; the Phase 4 notes above supersede its remaining-scope list.

Current focused checks: `node --test checks/workspace.test.mjs checks/capture.test.mjs checks/case.test.mjs checks/complaint.test.mjs`.

Phase 2 is now implemented: `/app` opens the introduction/overview and `/app/cases` opens searchable, filterable cases. Choose **Explore sample cases** on first visit, or use the **Demo workspace** menu to review empty/offline/error states. The app uses the same Nunito/Inter typography and foundation tokens as the revised landing. See PHASE-2-HANDOVER.md for routes, validation and remaining scope. Existing Phase 1 notes below are historical where superseded.

Optional focused logic checks: `node --test checks/workspace.test.mjs`.

The landing page has been revised to the approved consumer SVG direction: rounded self-hosted Nunito headings, larger body/product text, source-linked message artwork, licensed illustrative photography, labelled company examples and reduced-motion-aware animations. See LANDING-REVISION-HANDOVER.md for current validation and ASSETS.md for provenance. The earlier Phase 1 handover below is historical; app workflows still arrive in subsequent phases.

Phase 1: React + Vite + TypeScript + Tailwind CSS. Inter and IBM Plex Mono are served locally through @fontsource. Lucide supplies interface icons. React Router owns public `/` and reserved `/app/*` routes.

## Run locally (PowerShell)

```powershell
cd "C:\Users\Test\OneDrive\Documents\ChatGPT\PromiseKeeper - VIHAANX\bindr-app\frontend"
npm install
npm run dev
```

Open http://localhost:5173. No `.env` file is required for the default synthetic demo. Copy `.env.example` to `.env.local` to override public settings. `VITE_USE_MOCK=false` selects the HTTP adapter; `VITE_API_URL` is the API origin (default http://localhost:8000). The adapter appends /api/v1 unless already present, mapping the shared logical FRONTEND_API_BASE_URL setting.

```powershell
npm run typecheck
npm run build
```

## Phase 1 delivery

- Responsive marketing landing, approved headline and brand colors.
- Original SVG document-record illustration and vector rendering of the supplied Bindr logo.
- Interactive synthetic product preview: choose original/revised promise to inspect the linked source quotation.
- Three illustrated workflow steps, record principles, factual control/privacy section, keyboard-native FAQ, and working Contact/Privacy/Terms dialogs.
- Mobile navigation, reduced motion, visible keyboard focus, skip link, labelled dialogs and semantic page regions.
- Reusable button, input, alert, status and branding components.
- Exact contract types, HTTP adapter, synthetic read adapter and single mapping boundary. Components do not import fixtures.
- `/app/*` displays an explicit build checkpoint until subsequent phases. No real upload, AI, persistence or draft generation is implemented in this phase.

Logo geometry is a vector redraw of the user's supplied mark, normalized to the approved #3D4DD6. Custom artwork is native SVG; no stock photography, external image runtime or AI-image dependency. Research screenshots and archives were not copied into this repository.

## Render Static Site

Root directory: `frontend`; build command: `npm ci && npm run build`; publish directory: `dist`. `public/_redirects` is copied into dist. In Render's dashboard also configure a **Rewrite** with source `/*`, destination `/index.html`, action Rewrite, to ensure BrowserRouter deep links work (Render does not rely on a Netlify-style redirects file). Configure only public VITE variables here. Backend/AI credentials stay server-side. Deployment was not performed.

## Contract provenance / next phases

The downloaded main branch only had a README. Sibling docs/ reference files were downloaded byte-for-byte through the GitHub connector from `feature/integration` @ `70f2db0b16c06160a176155c7faa19e555c371ce`; they are not edited contracts or changes intended for a frontend commit. Original remote files still use the previous product name; the new UI/code uses Bindr.

Read PLAN.md and GAPS.md. Keep commits limited to frontend/. User reviews visuals; no browser screenshot loops are run.

Suggested commit: `feat(frontend): build Bindr foundation and evidence-led landing page`

Manual staging command (not executed): `git add frontend/`
