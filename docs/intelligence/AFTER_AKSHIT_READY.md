# Integration runbook — after Akshit's Track A is ready

Prepared 15 November 2026. This is a concrete test/coordination sequence, not release approval. B's work remains on its independent checkout; A-owned runtime files must be fixed in A's branch.

## What is ready before A finishes

- B's account-aware branch, pure intelligence seam, v2 client/capture/review components, independent fixtures and tests.
- The actual v2 capture screen is tested against a loopback-only fixture HTTP server, including an extraction that advances case version, double confirmation and an upload response lost after persistence. Exact retry keeps the operation key and saves one obligation.
- Serialized/reloaded actual case detail/history, evidence library/viewer, activity, complaint editor and plaintext export have controlled rendering tests. These extend local coverage; real browser/PDF/notification acceptance is still required.
- `INTERFACE_V2_B.md`, dependency requests and canonical input/expected-behavior hashes are ready for review. Test fixtures are not imported by production code.
- B commits can be transferred with the ignored local Git bundle under `storage/track-b-independent/Bindr-Track-B.bundle` when generated. Transfer does not deploy, send correspondence or activate providers. A must inspect/import into an independent checkout, not overwrite a dirty working tree.

## 1. Pin both branches and review the shared seam

Record A's exact branch/head, B's exact head, both test results and the common ancestor. Both must include account head `888722d1456380d4c5a370d15f49b7b9ee0d0c16` or its verified newer successor. Handoff snapshot is `7734a87`; do not replace either person's uncommitted work or squash the other's history.

Review concrete request/response details in `INTERFACE_V2_B.md` against A's actual API schema. Resolve discrepancies before enabling UI. In particular:

1. Completed extraction envelope/version and authenticated queued-job → proposal retrieval.
2. Review decisions, unselected-candidate policy, predecessor links and manual origins.
3. Capture draft create/update/discovery/restoration and expected versions.
4. Deadline-preview calendar ID/version, anchors, ranges and overrides.
5. Outcome allocations/corrections/reopen, export snapshot/download/retention and recent-auth deletion.
6. Provider-specific connection/pairing/reviewed-send/reply subcontracts and capability labels.

A imports `AIModuleAdapter.extract_proposals_v2(request)` for data-only suggestions. A performs authorization, retrieval and transactions. Agree any interface changes in both owned profiles/fixtures and the frozen shared contract through its designated owner; no silent guessed routes.

## 2. Build a combined local/staging candidate

A assembles the agreed integration branch from reviewed heads. Do not merge PR #4 or publish a deployment merely to make this convenient. Use isolated synthetic storage/database/accounts and record migration version. Review an upgrade from populated old data before touching real SQL.

Run the existing backend/AI suite, preserved integration regressions, frontend checks, `npm run check:track-b`, TypeScript/Vite build and the existing `checks/live-api.mjs` adapter smoke against the combined real local server. The optional B CI script is `frontend/checks/ci-track-b.sh`; A owns root CI incorporation.

Fix B-owned failures on B's branch and A-owned failures on A's branch. Keep the combined candidate reviewable; do not patch the other owner's internals to bypass a contract failure.

## 3. Verify the real core journey, without fixtures

| Scenario | Required connected observation |
|---|---|
| Airtel four obligations | All four facts/amounts/source quotes/individual dates survive extraction, subset/full review, SQL reload and another authenticated browser. No duplicate review on replay. |
| Original 5 / 8 / dated 1B | Configured real model completes the formerly blocked semantic scenarios. Unknown trigger stays conditional; Dec 28 + five calendar days comes from A's service as Jan 2; revision retains both sources/history. Record request/model/build/timing, not raw private evidence. |
| Invalid/conflicting/cancelled dates | Nov 31 warns with no normalization; communication provenance persists; conflicting/revoked history requires an explicit decision and retains prior rows. |
| Recovery/privacy | Real session expiry → same-account sign-in restores exact capture/review/manual text; another account cannot read it. Cloud-saved draft restore and cross-device isolation work. |
| Receipts | ₹500 → ₹200 confirmed receipt → ₹300 outstanding; pending/company claim does not reduce balance; remaining full receipt, correction and reopen retain the ledger. No mixed-currency total. |
| Stale tabs | Two actual tabs plus simultaneous PostgreSQL writes produce the agreed conflict behavior. Reconciliation preserves input; uncertain replay does not duplicate a case/original/outcome. |
| Truth in overview/agenda | Per-obligation state, case projection and currency totals agree with the server ledger and server `as_of`, including revisions, partial receipt, resolved/reopened and review-only records. |

Keep original verdicts beside the new observations. Passing schema/error tests or an offline provider result does not close a blocked semantic scenario.

## 4. Verify dependable workflows and real providers

1. Stored-XSS in a real browser across save/reload, detail/history, original evidence, activity, complaint, notification preview and PDF/bundle output; monitor scripts, events and remote loads. The new JSDOM matrix does not replace this.
2. Durable reminder delivery/cancellation/rescheduling with one configured transport; deletion cancels stale work and cleanup survives a retry/restart. Never send a test message through a real user's case without explicit recipient/content authorization.
3. Private consistent-version PDF/bundle/data exports; verify exact original digests with `/verify`, reject stale/cross-account access and validate actual retention explanations. Hash matches are not authorship/legal certification.
4. Dedicated controlled-account reset issuance, first use/reuse and session revocation; the user operates passwords/MFA. Preserve Google login and 6–128 policy.
5. Mixed PDF, real MSG sample after A's dependency review, tested-language OCR/transcription, installed phone share target and explicit Chrome capture/pairing. Unsupported capabilities remain disabled with working fallback.
6. Authorized case questions/citations and abstention, reviewed sending/reply dedupe/disconnect, draft-only follow-ups. Public aggregates require their reviewed privacy/sample contract and explicit release approval.

## 5. Review release separately

Once connected acceptance passes, record the combined commit, schema migration version, model/config identifier, exact tests and any remaining gate. Review migration backup, rollback, private storage and account defenses. Obtain deployment authorization before changing the existing service, then verify the actual deployed revision and saved records. No automatic merge/deploy is part of this runbook.

If a provider/account/service remains unavailable, finish independent checks and record its exact remaining owner action. Do not mark its feature accepted or replace it with a fixture success.
