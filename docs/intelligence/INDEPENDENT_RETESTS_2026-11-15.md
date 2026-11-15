# Additional independent work — 15 November 2026

This supplements the initial retest report. Original QA reports, initial retest results and frozen diagnostic assertions are unchanged. No A implementation, root configuration, cloud service or real credential was modified.

## Fixes made while A develops

- Bound each cached/retried v2 operation to its HTTP action and case path as well as account/payload. A cached success cannot be reused for another action/case.
- Prefer `__Host-bindr_csrf`, then account CSRF, then legacy CSRF, regardless of cookie order. Malformed cookies fail before a mutation is sent.
- Clear account identity on HTTP 401 even if an intermediary returns HTML instead of the API error envelope. The uncertain operation remains associated with the original account for safe reconciliation.
- Validate extraction envelopes before marking their operation succeeded. Preserve an explicitly returned `case_version` so review does not submit the stale upload version. Support raw proposal/queued-job responses without inventing a new retrieval route.
- Preserve v2 manual-entry wording/amounts and proposal edits/selection/date reasons in account-bound capture memory across auth-subtree remounts. Reauthentication requires fresh confirmation. Production activation remains disabled until the shared v2 profile is reviewed.
- Validate source count and empty/oversized originals before creating the case; serialize review/manual mutations with a common click guard.

## New test coverage

`stored-surfaces.test.mjs` serializes/reloads a synthetic case and mounts the actual saved detail/history, evidence library, activity, complaint editor and original evidence viewer. Script/event/remote-load monitors remain empty, Unicode/source markup remains literal, and HTML/SVG originals are not embedded. Plaintext export preserves the exact wording. These are React/JSDOM rendering checks with controlled retrieval/auth boundaries, not live browser or full security sign-off. Real notification/PDF output and cross-device checks remain pending.

`capture-v2-flow.test.mjs` mounts the actual capture/review screen with its real v2 client against a loopback-only HTTP fixture. It verifies extraction version 3 is used for review, double confirmation sends once, and an upload response lost after server persistence is replayed with the same key, producing one saved obligation at version 4. The server is synthetic; no real v2 acceptance is claimed.

The existing `checks/live-api.mjs` also passed against a separate real local FastAPI process on port 8032 with a dedicated synthetic SQLite/evidence directory. It exercised the actual frontend v1 HTTP adapter through session/create/upload/extract/review/revision/complaint/original-download/stale-write rejection/resolution. AI was explicitly offline mock; this proves neither live provider semantics nor real Firebase acceptance.

Final verification: **81 existing frontend checks passed; 21 expanded Track B checks passed; TypeScript/Vite production build passed**. The prior full Python result remains 235 passed + 3 subtests; this follow-up changes only owned frontend code/test fixtures and documentation. The frozen historical future-date probe remains preserved with its previously documented obsolete expectation; it was not rewritten or counted as a new success.

## After A is ready

Use [the integration runbook](AFTER_AKSHIT_READY.md): pin/review both heads and exact interfaces, assemble an isolated combined candidate, run the real core journey and provider/security/privacy checks, then review deployment separately. No production rollout or external correspondence is implied by local passing tests.
