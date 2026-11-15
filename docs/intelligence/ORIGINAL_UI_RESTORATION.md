# Restore the original default product UI

On 15 November 2026 the owner rejected the replacement integration capture UI after the fetch/dashboard hotfix. The earlier correction restored dashboard styling but still routed `/app/upload` to the plain `IntelligenceCapture` form. That did not restore the original product experience.

This correction changes route selection, rather than recreating or restyling the product screens:

| Normal route | Original component restored |
|---|---|
| `/app` | `Overview` |
| `/app/cases` | `Cases` |
| `/app/upload`, `/app/review`, `/app/capture-v2` | `Capture` |
| `/app/cases/:caseId` | Existing `CaseDetail`, unchanged |

The original capture includes upload/paste tabs, drag/drop and file queue, guidance panel, source preview beside the reviewed fields, confirmation and saved screens. Source comparison against preserved account commit `888722d` shows no changes to `Overview.tsx`, `Cases.tsx`, `CaseDetail.tsx`, `CaptureSource.tsx`, `capture.css` or `workspace.css`. `Capture.tsx` keeps its original presentation; its only earlier changes are a synchronous duplicate-save guard and confirmation of future communication dates. No markup was replaced in this correction. Account-aware capture recovery and the fetch receiver fix are retained.

The v2-only workspace/capture prototypes remain at explicit `/app/tools/workspace-v2` and `/app/tools/capture-v2` routes, outside normal sidebar navigation. The existing `/app/cases/:caseId/workflow` API-integration view also remains available. Backend v2 data and APIs are not removed, migrated back, or silently projected into v1 facts. The main original capture/review UI uses its existing v1 API adapter; it is **not** claimed to have been rewired to v2 by this route restoration. Completing that integration must preserve these original components and their design. Main v1 case totals do not include separately saved v2 obligations. This is a deliberate restoration with a recorded integration limitation, not full-roadmap acceptance.

Delivery uses the frontend-only hotfix utility and the existing v2 backend image by digest. It does not change account configuration, SQL records, originals, schema or the scheduled maintenance worker. The owner's screenshot confirms that the preceding frontend hotfix reached the browser; a returned revision/traffic record for that hotfix was not supplied. This restoration's cloud rollout has not yet been observed. No broad tests, real-browser acceptance or live model call was run in this correction.
