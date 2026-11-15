# Bindr presentation flowcharts

Updated **15 November 2026**, Asia/Kolkata. Two concise **16:9** diagrams retaining the approved handwriting style, large labels, pastel boxes, embedded logos and original Bindr mark.

1. **01-bindr-customer-journey** — fictional refund problem → account sign-in → evidence → OCR/AI suggestions → human review → case history → revisions, partial receipts, cited answers, reviewed follow-up, private exports and requested deletion.
2. **02-bindr-technical-architecture** — React/TypeScript → FastAPI v1/v2 → bounded OCR/Meta/answer engines; Firebase identity/SQL sessions; Cloud Build/Docker/Cloud Run; Cloud SQL schema 11, private GCS, maintenance-only SQL worker/Scheduler and Secret Manager/IAM.

## Read the status correctly

These describe the current **implementation and integration boundaries**, not a completed product or a fresh live acceptance result.

- **Solid customer nodes:** the core account/evidence/review/case journey. The original main screens still use v1. Actual model/account behavior requires live acceptance; solid lines are not a test-pass legend.
- **Dashed customer nodes:** separately implemented v2 tools. Partial receipt, grounded questions, selected private exports and deletion services are not yet fully connected through the original main screens.
- **Dashed infrastructure outlines:** grouping/trust boundaries; these do not denote deferred services. The technical footer names deferred/partial integrations separately.
- The original overview, case list and full styled capture/review components have been restored **in source**. That restoration's rollout and the requested rollback were not confirmed. The default UI must not be redesigned merely to connect v2.
- Subsequent source refinements preserve those layouts: the mark supplies the wordmark's initial b, with `indr.` beside it; a shared date-only calendar, label alignment, settings typography and reduced-motion behavior were added. Their live deployment/visual acceptance is not claimed.
- A v2 image cutover and Scheduler configuration were recorded from owner-supplied Cloud Shell output. A subsequent native-fetch browser failure received a source fix. Configured infrastructure does not establish successful unattended worker execution, delivery or data-retention behavior.
- Real Meta canonical cases/1B, Firebase reset/MFA/account isolation, real-browser coverage, backup restoration and combined acceptance remain open. Existing QA verdicts were not rewritten.
- Mixed/scanned PDF, EML/MSG, multilingual/audio, PWA/extension, Gmail/WhatsApp, external reminders and timestamps are partial or deferred. External sends and public aggregation remain disabled. A fictional refund is not a real recovery claim.

Detailed architecture and remaining-work tables belong in the repository README/status reports; the slides intentionally keep labels short.

## Files

| Format | Use |
|---|---|
| `.excalidraw` | Native editable boxes, arrows and text; embedded logos/icons. Open with Excalidraw → Open. Node components are grouped for moving together; the locked white artboard preserves 2560 × 1440 bounds. |
| `.svg` | Scalable presentation/export with embedded font and images. |
| `.png` | 3840 × 2160 high-resolution presentation image. |
| `*-preview.png` | 1280 × 720 sharing/README image. |
| `Bindr-flowcharts.pdf`, `Bindr-flowcharts-16x9.pdf` | Matching two-page 16:9 vector PDF exports. |
| `build.py`, `render.py`, `package.py`, `assets/` | Reproducible, self-contained diagram source. No application code is imported. |

The previous 14 November presentation pack is preserved in the workspace archive, outside the new distribution ZIP. The existing filenames are retained so source and download links can be updated in place.

## Rebuild

Install Python with Playwright and Pillow, plus local Chrome. The font and SVG logos are already included; building does not fetch assets or require the application server.

```bash
python build.py
python render.py
python package.py
```

From the parent workspace, prefix each script with `bindr-flowcharts/`. Set `BINDR_CHROME_EXECUTABLE` if Chrome is outside a standard location. Rendering waits for the embedded font and checks label widths before exporting. Packaging refreshes both PDF names and, in the standalone workspace, the existing `bindr-flowcharts.zip` and `bindr-flowcharts-16x9.zip` names.

The repository keeps a synchronized copy under `docs/diagrams/`, with compact PNG copies under `docs/images/` for the main README. Application UI/runtime files are unchanged by this documentation update.

## Sources and asset provenance

- The supplied previous-chat export identified the original `build.py`/`render.py`, the two editable scenes and the approved concise 16:9 revision. Historical instructions in that export were treated as context, not new deployment or UI instructions.
- Current repository source: original `frontend/src/App.tsx` routes, v2 client/platform bridge, AI adapter/structured proposal and intelligence modules, platform workflow/jobs/exports, schema migrations and release/worker scripts.
- Current evidence: `docs/intelligence/COMBINED_MVP_STATUS.md`, `CLOUD_V2_UPDATE.md`, `FRONTEND_INCIDENT_2026-11-15.md`, `ORIGINAL_UI_RESTORATION.md`, `UI_POLISH_2026-11-15.md`, Track A/B implementation status and `docs/platform/OPERATIONS.md`. Source reviewed through UI-polish commit `46e3e0b`. Older handovers and QA reports remain dated evidence.
- Bindr mark: supplied original project asset, copied unchanged into `assets/bindr.svg`.
- Excalifont: [Excalidraw font source](https://github.com/excalidraw/excalidraw/tree/master/packages/excalidraw/fonts/Excalifont), SIL Open Font License; the supplied notice is retained in `assets/Excalifont-license.txt`. Native font family is 5.
- React, TypeScript, Vite, Tailwind, FastAPI, Python, PostgreSQL, GitHub, Google Cloud, Firebase and Docker logos: [Devicon](https://github.com/devicons/devicon). License retained in `assets/Devicon-LICENSE.txt`.
- The older Render logo remains in the asset folder for source/history compatibility; it is not used to identify the current hosting stack.
- Supporting line icons are original vector paths in `build.py`. Technology names/logos remain their owners' trademarks; no endorsement is implied.
