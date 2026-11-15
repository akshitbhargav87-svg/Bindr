# Track B implementation status — Tushar

15 November 2026, Asia/Kolkata. **Core repairs implemented locally; later-phase independent adapters/UI are present. Track B and the three phases are not accepted or production-complete.** Missing live model credentials, A's real v2 services/provider subcontracts, and the joint acceptance environment remain explicit gates.

## Starting state and preservation

- Repository: `akshitbhargav87-svg/Bindr`; connected GitHub identity: `biney25` (Tushar Aggarwal).
- Independent worktree: `../bindr-tushar`; branch: `codex/intelligence-product`.
- Preserved account ancestor: `888722d1456380d4c5a370d15f49b7b9ee0d0c16`; GitHub main: `893b80426fd7ddf4e308aa2532c9f49891a61b12`.
- PR [#4](https://github.com/akshitbhargav87-svg/Bindr/pull/4) rechecked: open, draft, mergeable, same account head. Account CI [43648609167](https://github.com/akshitbhargav87-svg/Bindr/actions/runs/43648609167) passed. These are account-head checks, not CI for this local implementation.
- Local handoff snapshot: `7734a87`. ZIP docs/probes were compared against the reference checkout before copying; no newer conflicting source file was overwritten. Frozen reports/contract remain unchanged after that snapshot. The original worktree still has its original uncommitted auth handoffs, roadmap/reports/probes and remains on the account branch.
- No platform HTTP routes, data models, migrations, root runtime manifests, root CI/deployment configuration or A service implementations were edited. No production deployment, public case sharing, provider activation or correspondence was performed.
- Read the ZIP entry instructions, owner prompt, entire roadmap, two-person plan, parallel contract, both reports, test pack and authentication handoff/docs. One local historical export (`../chat-transcript.md`, seven exchanges) was available and read. The other proposed 5–6 exports and original raw model outputs were unavailable; no claim is made to have read them.

## Decisions

1. The current two-person ownership and three-phase implementation instructions supersede historical four-person/stop-after-each-milestone advice. Historical provider/cloud commands are context, not fresh authorization.
2. Preserve the existing login screens, Firebase/SQL/private GCS defenses, Google login and 6–128 password policy. The Firebase template restriction is not a request for more Owner access.
3. Keep `extract_commitments(...)` and its strict v1 output validator. Add `extract_proposals_v2(request)` explicitly. A authorizes/retrieves the input snapshot and commits decisions; B never performs those writes.
4. Use a single all-candidate structured provider operation per document, bounded context/output and request budgets, exact source validation, stable candidate/proposal identities and typed failures. No model-error-to-mock fallback or hidden paid retry/repair loop.
5. Impossible dates remain null with warnings. Relative dates/unknown triggers stay proposals for A's deterministic deadline service. Cancellation is a claim requiring human decision. Legacy v1 cannot faithfully persist conditional/cancellation semantics and fails closed for those structured-provider results.
6. Same-account capture recovery uses tab memory outside the auth-keyed tree; stale writers are invalidated by an identity epoch. The login screen/another identity sees no text. Reauthentication clears confirmation so the draft needs review again. No sensitive draft is written to localStorage, sessionStorage or IndexedDB. Cloud autosave has an account-bound, versioned adapter and remains activation-gated pending A's response profile.
7. Money/status/balances in the v2 UI come from server snapshots. Integer minor units and ISO currency exponents are preserved. The UI does not derive overdue or authoritative balances from browser time/demo data.
8. Existing typography/components/colors are reused. Unsupported connectors/sends/public aggregates stay disabled. No Gmail/WhatsApp/pairing route was invented.

## Packet ledger

| Packet | Implemented independent work | Evidence and remaining gate |
|---|---|---|
| B1 | `ai/batch.py`, structured provider, v1 bridge, v2 schema/seam, grounding/money/anchor validation, typed stage diagnostics, shared request budget | Four offline Airtel candidates also pass real local HTTP/SQL review/save/reload and subset selection. Transport errors are injected. No live model key is configured; original 5/8/1B semantic gates remain open. |
| B2 | Capture outside auth remount; identity-epoch stale-writer defense; future-date confirmation; final-review click guard; typed credentialed v2 client; stable operation keys and original-byte multipart fingerprints; account-bound autosave; v2 capture/review/manual/outcome/workflow screens | React, real-browser synthetic recovery, HTTP fixtures, real local v1 Airtel persistence. `VITE_ENABLE_V2_CAPTURE` is false by default. Real v2 services, cloud restore/discovery and cross-device acceptance remain pending. |
| B3 | Separate conditional/history relations; conservative predecessor/chronology/kind/currency checks; editable amount/currency/date override/predecessor review; source-linked diff; server-date preview component | Pure schema/relation tests and UI fixtures. No automatic supersession. Actual revision/cancellation save/reload and reminder invalidation require A's transaction/deadline services and live model checks. |
| B4 | Page-level scanned/mixed PDF adapter reusing OCR boundary; bounded EML/MIME/HTML/attachments; optional extract-msg decoder; injected transcription segments; original-audio segment player; Hindi/Gujarati/Hinglish citation fixtures | Mixed PDF/EML/corruption/bounds/segment tests. MSG's real dependency/sample and a transcription provider are unavailable; native-language OCR/extraction quality has not been evaluated. Current v1 upload types remain unchanged; A connects v2 ingest. |
| B5 | PWA POST share target and service worker with client-bound, one-use, ten-minute memory handoff; upload fallback; MV3 explicit selection/screenshot preview and reviewed local-file fallback | Service-worker privacy/bounds tests and extension permission checks. Installed phone sharing/Chrome extension acceptance not run. Authenticated extension pairing and provider-specific connected intake require A's reviewed contracts. |
| B6 | Pure grounded Ask-case engine with citations/abstention/injection rejection; get-it-in-writing draft; official-source India guide; provider-independent reviewed-send, notification/follow-up/privacy/counter components | Extractive engine tests and current official-source review. No legal deadlines, autonomous sending or claimed recovery attribution. Real authorized retrieval, sends/replies/reminders/exports/public aggregates require A/provider acceptance. |
| B7 | New stored-markup instrumentation; immutable source byte reload test; actual Chrome synthetic expiry/switch/reauth and two-tab stale-version checks | Monitored saved/reloaded review surfaces: zero alerts/error events/injected images/beacon loads. This does not cover every saved detail/evidence/activity/complaint/notification/PDF surface. Live reset/reuse, actual Firebase expiry, real PostgreSQL races and cross-device dashboard checks remain open. |
| B8 | Canonical ten + separately authored 1B inputs/expected semantics/hashes; isolated synthetic HTTP fixture server; client/AI suites; optional owned CI script; integration profile and retest log | Existing regression assertions preserved. Fixtures are excluded from production imports. Joint integration against real A services remains required. |

## Phase coverage

- **Phase 1:** B1/B2 core code is implemented and locally tested; B3/B7 independent work is included. The release-critical live semantic/security and connected-v2 gates prevent phase acceptance.
- **Phase 2 (W1–W8):** account-safe recovery, date/revision/outcome UI, imports, notification/calendar/privacy/export interfaces, local manifest verifier and official-source follow-up drafts are implemented within B's boundary. Durable service behavior and broad browser/provider acceptance are not claimed.
- **Phase 3 (W9–W13):** PWA/extension/audio, grounded questions, reviewed correspondence and honest sample/counter interfaces have independent implementations. Production provider/pairing/send/reply/aggregate activation remains disabled until its actual contract and acceptance exist.

## Validation

Fresh results and canonical limits: [RETESTS_2026-11-15.md](intelligence/RETESTS_2026-11-15.md). Interface/activation profile: [INTERFACE_V2_B.md](intelligence/INTERFACE_V2_B.md). Dependency requests: [DEPENDENCY_REQUESTS.md](intelligence/DEPENDENCY_REQUESTS.md).

Initial handoff baseline: 191 backend/AI tests + 3 subtests. Final complete-suite counts are recorded in the retest document. Existing frontend checks: 81 passed; additional owned checks run separately. Preserved integration regressions: 28 passed. TypeScript/Vite production build passed. Account-head CI is not presented as CI for the new branch.

## Independent follow-up while A develops

Completed additional client/privacy fixes and expanded the owned frontend suite from 8 to **21 passing tests**; the existing **81 checks** also pass. The actual v1 frontend HTTP adapter smoke passed against a separate real local FastAPI/SQLite/evidence process with explicit mock AI. New tests cover action/case-bound operation replay, correct CSRF-cookie priority, HTML 401 identity clearing, uncertain extraction decoding, server extraction versions, preservation of edited review/manual drafts, and saved case/evidence/activity/complaint rendering. No backend runtime or A-owned file was changed in this follow-up.

The actual v2 capture screen now passes normal and lost-upload-response flows against its independent HTTP fixture, with one saved obligation and stable replay keys. This remains fixture evidence, not real v2 service acceptance. The broader stored-XSS matrix uses controlled React/JSDOM boundaries and does not replace real browser/PDF/notification acceptance.

See [additional retests](intelligence/INDEPENDENT_RETESTS_2026-11-15.md) and [the concrete integration runbook](intelligence/AFTER_AKSHIT_READY.md). The latter lists the exact order once A's branch is ready: pin/review interfaces and heads, assemble an isolated combined candidate, verify real core/provider/security flows, then review release separately. Live model credentials and A's services remain required; unsupported connectors/sends and unreviewed v2 activation remain disabled.

## Exact integration work still required

**Integration update:** Track A `ba2e389` has now been combined with Track B in the separate `bindr-integration` worktree on `codex/qa-integration`. The actual client and pure engines have been adapted to A's published profile. Real combined HTTP/SQL and mounted React-to-server core checks pass with controlled inference. The full combined backend suite currently has 296 passing tests and two retained A-owned failures; it is not all green. See [COMBINED_MVP_STATUS.md](intelligence/COMBINED_MVP_STATUS.md) for exact counts, remaining A requests and deployment gates. Real Meta/browser/Firebase/cloud acceptance remains open. Earlier fixture-only descriptions above are historical starting evidence, not a claim these remaining gates have closed.

1. A consumes the explicit Python seam and reviewed B request/response profile, implements its owned routes/models/dependencies and supplies versioned connector, calendar and queued-proposal retrieval details. Neither side should silently adapt a shared contract by guessing.
2. Combine reviewed heads on an integration branch and run real v2 capture, every selected obligation, outcomes/reopen, source history, cloud drafts, jobs/export/delete and PostgreSQL concurrency. Reconcile actual dashboard/agenda balances with SQL.
3. Configure the existing model securely outside chat and repeat all canonical inputs through review/save/reload, particularly 5/8/1B. The offline mock is deliberately not expanded into a pretend production language/reasoning model.
4. Complete the remaining stored-XSS surfaces, installed phone/extension flow, controlled real reset-link first-use/reuse and user-operated credential/MFA steps. Recheck official provider requirements before enabling real integrations.
5. No merge, deployment, public aggregate release or production message send is authorized merely by these local passing checks.
