# Deployed workspace failure and frontend hotfix

Owner screenshot after the first v2 cutover shows a signed-in workspace at `/app` displaying `Failed to execute 'fetch' on 'Window': Illegal invocation`. The screenshot also shows the integration workspace's bare layout and developer-facing v1/v2 copy replacing the earlier dashboard. Initial deployment success did not establish working browser acceptance. The earlier QA reports and local suite counts remain unchanged.

## Cause and correction

`V2Client` stored the browser's bare `fetch` function as a class property and invoked it as `this.transport(...)`. Chromium applies the client instance as receiver and rejects that native Window method invocation. The default transport is now an arrow that calls `globalThis.fetch(...)`, preserving the browser receiver. This shared fix covers workspace, capture, review and other inherited requests. Source search found no other stored bare fetch transport in the application; private download and v1 clients call fetch directly.

The connected workspace now reuses the existing `PageHeading`, summary strip, `CaseList`, status labels, loading/empty/error states, search and filter styling. Earlier saved cases retain their original case links and independently sourced server status/amounts. Connected cases link to receipt/revision workflows; no v1 amounts are silently merged into v2 money. Raw browser exception text and internal v1/v2 contract copy were removed from the dashboard. The capture page's self-referencing "Open existing capture" link was replaced with a workspace link.

The owner was given a traffic-only rollback command to `bindr-00003-cm9`. Execution of that rollback has not been observed. No database restoration, record deletion or secret rotation is part of the hotfix.

## Delivery and verification boundary

- TypeScript/Vite production build with real HTTP client and v2 enabled: **PASS**, 14.14s, existing chunk-size/import warnings. The subsequent capture-link/copy edits do not change imports or types; the cloud build compiles them again.
- No broad test rerun, native-browser verification or live model request was performed; the owner had requested no further test runs. A successful build alone does not exercise native fetch receiver behavior.
- `Dockerfile.frontend-hotfix` builds assets over the immutable, already-deployed v2 backend/OCR image. `scripts/release_frontend_hotfix.py` reads that base revision digest, builds the frontend image, preserves existing runtime/secret references, starts it without traffic, checks the named revision's readiness/image/environment/runtime identity/Cloud SQL attachment, then explicitly switches traffic.
- This path does not rerun schema migration, backups or worker provisioning. It supports either the still-active v2 release or the owner-restored older traffic target, while retaining the existing v2 backend image as base. The build introduces normal Cloud Build/Artifact Registry usage; application settings/IAM remain in place.
- Hotfix rollout has **not yet been observed**. Record the returned source/image/revision and traffic output separately after the owner executes it. The release record is written under ignored `storage/frontend-hotfix-*.json` in Cloud Shell.
