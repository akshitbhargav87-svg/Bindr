# Bindr frontend

React 19, TypeScript and Vite implement the original landing, overview, case list, upload/paste, side-by-side review, case timeline, complaint drafting, agenda and Settings. The design uses Nunito headings, Inter body text and the shared indigo/white workspace components. The latest refinements add the corrected wordmark, uniform account typography, aligned field labels, a date-only calendar and reduced-motion-aware feedback.

The [root README](../README.md) and [current integration status](../docs/intelligence/COMBINED_MVP_STATUS.md) describe current source and known limits. Earlier `PHASE-*`, `GAPS.md` and handover documents are historical implementation snapshots, not current launch acceptance.

## Start the standalone demo

From a repository checkout:

```text
cd frontend
npm ci
npm run dev
```

Open the Vite URL printed in the terminal, normally `http://localhost:5173`. Demo mode is the default when `VITE_USE_MOCK` is not exactly `false`. It uses synthetic in-memory data and does not prove real AI, account access or persistence. No secret belongs in a `VITE_` variable.

## Connected app

The deployed Docker image builds with:

```text
VITE_USE_MOCK=false
VITE_API_URL=/api/v1
VITE_ENABLE_V2_CAPTURE=true
```

Use the [root local-run instructions](../README.md#run-locally) to build the frontend and serve it with FastAPI from one origin. For separate Vite/API development, configure the public `VITE_API_URL` to the backend's `/api/v1` URL and use matching hostnames with the server's exact CORS/CSRF allowlist. The Vite config does not define an API proxy. A bare `.env` file is not a backend configuration loader.

`VITE_ENABLE_V2_CAPTURE` enables the relevant data/tool paths and account draft autosave. It **does not replace the original product screens**. Their main capture/review data path is still v1; wiring the v2 ledger into these components remains unfinished. The standalone v2 tools use the explicit `PlatformClient` adapter for Track A's published wire profile. Fixtures are test-only; application code does not silently switch a failed HTTP/model request to demo data.

## Routes

| Route | Screen/data boundary |
|---|---|
| `/` | Landing page |
| `/login`, `/register`, `/forgot-password`, `/auth/action` | Firebase-backed account screens and action-link handling |
| `/app`, `/app/cases` | Original overview and searchable case list, v1 facts |
| `/app/upload`, `/app/review`, `/app/capture-v2` | Original styled capture and explicit review, v1 adapter |
| `/app/cases/:caseId`, `/app/cases/:caseId/update` | Original source-linked case detail and communication/revision review |
| `/app/evidence`, `/app/drafts` | Evidence library and complaint drafts |
| `/app/agenda`, `/app/activity`, `/app/settings`, `/app/help` | Deadlines, activity, preferences/account security and help |
| `/app/cases/:caseId/workflow` | Separate v2 receipt, revision, answer, export and deletion workflow |
| `/app/tools/workspace-v2`, `/app/tools/capture-v2` | Separate v2 integration views; not default sidebar screens |
| `/app/share` | Shared-content review before capture; installation/browser support required |

Main v1 amounts are not silently combined with separately saved v2 obligations. Unsupported lifecycle/provider actions remain explicitly unavailable. The date picker returns `YYYY-MM-DD`; deadline interpretation remains a separate reviewed operation.

## Commands and evidence

```text
npm run typecheck
npm run check
npm run check:track-b
npm run build
npm run build:http
```

`check` covers the original frontend/account adapters and UI regressions. `check:track-b` covers the independent v2 transport, recovery and source/security fixtures. These do not prove real-browser/provider acceptance. A connected build must explicitly set the public flags above; an unconfigured local `build` uses demo mode. `build:http` forces HTTP mode and writes `dist-http`; regular `build` writes `dist`. Dependencies and generated outputs are ignored by Git.

Read the [UI incident](../docs/intelligence/FRONTEND_INCIDENT_2026-11-15.md), [original-screen restoration](../docs/intelligence/ORIGINAL_UI_RESTORATION.md), [UI refinements](../docs/intelligence/UI_POLISH_2026-11-15.md) and [deployment record](../docs/intelligence/CLOUD_V2_UPDATE.md) for the exact verification boundaries. Historical passing counts are not a fresh green run of the latest source.

## Deployment

Google Cloud is the current target. [Existing-service rollout](../docs/intelligence/CLOUD_V2_UPDATE.md) handles schema/worker requirements; `scripts/release_frontend_hotfix.py` handles frontend-only replacement over an existing immutable backend image. Git pushes and PR merges do not automatically deploy. The previous Render hosting notes are historical.
