# Bindr frontend

The frontend implements the landing, workspace, capture/review, source-linked case timeline, outcomes, complaint drafting, agenda, activity and settings. It uses one Nunito/Inter design system with #3D4DD6, white/cool-grey surfaces, 1px borders and no shadows.

Default mode is a deterministic local demo. Supported HTTP flows are wired and transport-tested; testing against the real backend is pending because localhost:8000 was unavailable. Read INTEGRATION-HANDOVER.md and GAPS.md before switching modes. Historical per-phase handovers document earlier checkpoints; PHASE-6-7-HANDOVER.md is the current completion record.

## Run in Command Prompt

From a fresh Command Prompt:

```cmd
cd /d "C:\Users\Test\OneDrive\Documents\ChatGPT\PromiseKeeper - VIHAANX\bindr-app\frontend"
npm run dev
```

Open http://127.0.0.1:5173. This checkout already has dependencies; use npm ci for a fresh installation. No .env is needed for demo mode.

## Routes

| Route | Purpose |
|---|---|
| / | Approved marketing landing |
| /app | Introduction / overview |
| /app/cases | Searchable, filterable cases |
| /app/cases/:caseId | Case, preserved promise history and original evidence |
| /app/cases/:caseId/update | Match a communication, review a new/revised promise, or retain evidence |
| /app/upload; /app/review | Capture and explicit confirmation |
| /app/evidence | Searchable original-evidence index and viewer |
| /app/cases/:caseId/complaint | Facts → Draft → Review → Export |
| /app/drafts | Tab-local saved complaints |
| /app/agenda; /app/activity | Deadline agenda and local activity/read markers |
| /app/settings; /app/help | Calendar assumptions, real in-app preferences and guidance |
| /app/archived | Mock archive/restore view |

Desktop sidebar and written four-tab mobile navigation share the same pages. Mobile secondary links expose Deadlines, Activity and Drafts. User visual/device review remains necessary; route response checks do not certify rendering.

## Commands

```cmd
npm run typecheck
npm run check
npm run build
npm run build:http
```

check runs 55 focused tests, including a temporary loopback HTTP contract server that closes afterward. build outputs the default demo to dist. build:http forces VITE_USE_MOCK=false and outputs to dist-http, leaving the demo configuration/output alone. Both generated folders are ignored. No dependencies were added in Phases 2–7.

## Demo and connected data

Demo cases, originals, outcomes and annotations live in memory until reload. The fixed reference date is 14 Nov 2026 in the mock adapter only. Screenshot/PDF originals can be viewed/kept and entered manually; local extraction reads UTF-8 text, not OCR. The Demo workspace menu identifies fixtures and exposes empty/offline/error states.

Capture and complaint state survive workspace/public navigation within this app session. Saved complaints are explicit copies for this tab only. Reload warnings protect local work. Only introduction/demo-view preferences and two in-app preference booleans use localStorage; original files, document content and activity read-marker IDs do not.

HTTP uses VITE_USE_MOCK=false and public VITE_API_URL (default http://localhost:8000; /api/v1 is appended unless already supplied). VITE_API_URL maps the shared logical FRONTEND_API_BASE_URL setting and may also be /api/v1 for same-origin hosting. Backend session bootstrap, cookie credentials, CSRF and exact CORS origin must be supplied by the backend owner. Match browser/API hostnames. No backend or AI secrets belong in frontend variables.

HTTP supports UTF-8 text/text-layer PDF, create/read/upload/extract/review/revision/full resolution/complaint preview/original download. Unsupported features remain isolated local extensions or are blocked; see GAPS.md. HTTP errors never fall back to sample data, and POST requests are never automatically retried.

Complaint export is reviewed plain text: clipboard or local UTF-8 .txt, optional history and filename index. No PDF, bundled originals, automatic filing, external notifications or background scheduler is included.

## Integration and hosting

INTEGRATION-HANDOVER.md gives exact commands for a second connected frontend on port 5174, backend prerequisites, tested transport boundaries and the pending real-server verification path. No backend code, shared contracts or root configuration was modified.

Render Static Site: root frontend, build npm ci && npm run build, publish dist. Set public variables before building. Configure an explicit Rewrite from /* to /index.html for BrowserRouter deep links. public/_redirects is included but does not replace Render's dashboard rewrite. No deployment was performed.

## Ownership and manual commit

All implementation changes are inside frontend/. Reference docs/ stays untracked/read-only. Research screenshots remain outside the repo; ASSETS.md records existing landing asset provenance. The assistant performs no Git writes.

Suggested final commit: feat(frontend): finish agenda preferences and API integration checks

Exact staging command from the repository root: git add -- frontend/

See PHASE-6-7-HANDOVER.md for the complete fresh-CMD commit/push/verification sequence. Copy command lines only, without Markdown formatting markers.
