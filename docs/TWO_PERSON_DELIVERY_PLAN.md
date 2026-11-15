# Two-person delivery plan — Akshit and Tushar

15 November 2026. Supersedes historical four-person ownership and the single-agent sequential prompt. This is a planning revision only; no defects have been fixed by writing it.

## Independence and balance

**Akshit (A): platform, persistence, API, jobs and service integrations. Tushar (B): AI/document intelligence, product UI, browser/mobile capture and UX verification.** Each owns a complete testable subsystem. B's AI work is deliberately included to balance A's service/data work; this is not a frontend-only assignment.

Neither waits for the other's implementation or PR. Both start from the same pinned account-aware base, implement against `PARALLEL_IMPLEMENTATION_CONTRACT.md`, keep local fixture adapters and run independent contract tests. B uses synthetic HTTP handlers for pending A endpoints; A injects a deterministic intelligence provider for pending B behavior. Both also run regression tests against the baseline real module. Test doubles are excluded from production bundles/configuration and never count as connected acceptance.

The integrated app necessarily connects both subsystems. **Independent development is feasible; zero runtime/integration dependency is not.** No per-ticket handoff or “finish backend first” workflow is required. A final combined branch validates real adapters, migrations and UI together. Contract changes are exceptional, backward-compatible/versioned and reviewed by both; meanwhile both keep implementing the agreed version.

Rough relative effort, not hours or an estimate of guaranteed equal time:

| Packet | Akshit / A | Points | Tushar / B | Points |
|---|---|---:|---|---:|
| 1 | A1 Migration baseline, idempotency, date/draft primitives | 6 | B1 Extraction reliability, multi-promise engine and typed provider failures | 6 |
| 2 | A2 Outcome ledger, deadline service, revisions/manual persistence | 6 | B2 Auth-safe capture recovery, multi-item review, calendar/outcome UI | 6 |
| 3 | A3 Durable jobs, reminders, follow-up scheduling, deletion/retention | 6 | B3 Conflict/revocation reasoning, source diff, conditional/date reasoning UX | 5 |
| 4 | A4 Private PDF/bundle exports, integrity/timestamp service | 4 | B4 PDF/email/audio processing, multilingual fixtures/citations | 6 |
| 5 | A5 Inbound email/Gmail/WhatsApp server connectors | 6 | B5 PWA/share target, Chrome extension, connected capture UX | 5 |
| 6 | A6 Authorized retrieval APIs, connector credentials, escalation/aggregate data | 5 | B6 Ask-case grounded engine, escalation/get-it-in-writing/editor/counter UI | 5 |
| 7 | A7 Account/live API, PostgreSQL races, abuse/operations verification | 4 | B7 Stored-XSS browser tests, auth/reset UX, real tabs/mobile/dashboard checks | 4 |
| 8 | A8 API contract fixtures, service CI/release preparation | 3 | B8 Client/AI contract fixtures, UI build/evaluation packaging | 3 |
| Total | | **40** | | **40** |

If evidence changes estimates, move a **whole isolated optional adapter** (with tests/file ownership) by a written mutual update, not miscellaneous files or shared edits. Do not sacrifice repair/security acceptance to equalize arbitrary point totals.

## Exclusive ownership

| Owner | Files/directories |
|---|---|
| A | `backend/app/api/**`, `backend/app/models/**`, `backend/app/schemas/contract.py` plus new API schemas, `backend/app/core/**`, `backend/app/services/**` **except** existing `ai_adapter.py` and new `intelligence/**`, new `backend/migrations/**`, all Python runtime/DB requirement files, `scripts/**`, root Docker/Cloud Build/deploy/CI configs, new `tests/contracts/platform/**`, backend tests except the B-owned list below |
| B | `frontend/**` including npm manifests/lockfile/checks; `backend/app/ai/**`; existing `backend/app/services/ai_adapter.py`; new `backend/app/services/intelligence/**`; new `extensions/**`; `backend/app/tests/test_ai_adapter.py`; new `backend/app/tests/test_intelligence_*.py`; AI tests and new `tests/contracts/intelligence/**` |
| A documents | New `docs/platform/**`, `docs/IMPLEMENTATION_STATUS_A.md`, API/deployment guides and root README updates |
| B documents | New `docs/intelligence/**`, `docs/IMPLEMENTATION_STATUS_B.md`, frontend/AI guides |
| Frozen during parallel work | This plan, main roadmap, parallel contract, prompts, original QA reports/test pack, shared existing regression assertions/fixtures. Submit proposed revisions separately; A incorporates agreed root-doc/contract changes, B reviews them. No competing edits to the same files. |

`ai_adapter.py` mixes provider orchestration and validation today; **B owns the whole existing file**, not individual functions. A owns the HTTP request handler and transaction. A imports only the agreed interface and never patches B internals to make a test pass. B's business reasoning/answer engine returns data; SQL/auth/retrieval is A's responsibility. Dependency requests from B go into `docs/intelligence/DEPENDENCY_REQUESTS.md`; A pins approved Python dependencies/root build changes, while B can test from an isolated optional requirements file under its owned AI directory. No secrets in either artifact.

Existing `test_extreme_pack.py` is A-owned. Its React counterpart is B-owned. Neither edits shared baseline assertions to make a failing requirement green. Current diagnostic probes intentionally confirm some missing behavior; retain their original findings and add desired-behavior retests. Before release update diagnostic expectations explicitly with evidence so old assertions do not misleadingly require known defects forever.

## Three delivery phases, both owners working in each

### 1. Repair the core and remove blind spots

**A1/A2/A7 and A3 foundations:** real migration tooling; safe operation keys and duplicate PNG policy; server date/provenance/draft recovery; transactional outcomes/manual entries; fixed-clock deadlines, invalid-date warnings and conditional-anchor status; preserved revisions/cancellation events; PostgreSQL overlap test. Build draft/job/delete contracts now even if transport activation comes later.

**B1/B2/B3/B7:** provider-stage diagnostics, timeouts/output failures, all four Airtel candidates, no-promise/cancelled/conditional discrimination, safe invalid date handling; lossless same-account capture recovery, review/outcome controls and explicit date warnings; actual stored-XSS instrumentation and original regressions. Work against agreed synthetic responses while A implements routes.

**Required retests:** all ten canonical AI pack fixtures and 1B (fresh results, not rewritten original history); REC-001 partial/pending/full paths; P2 duplicate/date/expiry findings; remaining partial/blocking criteria. Reports currently show no universal prompt-injection safety proof or invalid-date persistence proof. Reproduce before asserting cause. `/auth/action` already passed a limited local-render/live-HTTP check; obtain contrary evidence before reopening it as a current 404 defect.

### 2. Complete the dependable workflow

**A3/A4/A7:** complete durable reminders with real delivery evidence, cancellation/rescheduling and deletion cleanup; ledger/reopen/export/snapshot APIs; private bundle/verification; account-wide export/delete; migrations/backups/restore. Authentication real reset flow uses dedicated controlled account; the user enters credentials/new passwords.

**B2/B4/B6/B7:** multi-obligation agenda/health/balances, actual two-tab conflict UI, recovery/retry; scanned/mixed PDFs, EML/MSG and tested multilingual processing; export/privacy/notification controls and factual escalation/get-it-in-writing drafts. No arbitrary region/language claims or legal deadlines.

W1–W8 from the main roadmap remain fully in scope; repair-phase parts are reused.

### 3. Connected capture/intelligence and release

**A5/A6/A8:** webhook verification/deduplication, inbound aliases, OAuth token custody, Gmail delivery/replies, supported WhatsApp service, authorized retrieval, follow-up jobs, aggregate privacy/withdrawal data, timestamp provider and deployment preparation.

**B4/B5/B6/B8:** phone share/extension explicit capture, audio/transcription segments, cited question answering/abstention, connector UI, reviewed send UI, follow-up prompts, personal/global counters and scoreboard display with denominator/sample/privacy limits.

W9–W13 remain in scope. Account/provider/paid-service blocks are documented precisely and do not stop independent work. Public aggregates and automatic correspondence remain disabled without applicable authorization/review. No user-owned production message is sent just for a test.

## Coverage ledger

| Requirements | A responsibility | B responsibility |
|---|---|---|
| AI-001/AI-002; Tests 5/8/1B blocked | Request deadline/job/error plumbing, operational evidence | Provider/engine diagnosis and completed semantic retests, recovery UI |
| MULTI-001/Test 3 | Multi-candidate transaction/version/idempotency | Four-candidate extraction/source linkage and subset-review UI |
| DATE-001/Test 7, P2-08, W2 | Persist/validate anchor + deterministic calendars/ranges/holiday version | Language/conditional/invalid-date suggestions and visible warnings/confirmation |
| REV-001/Tests 1/9/1B, W3 | Immutable history, cancellation/claim records | Reasoning/diff and user decision, no auto-revocation |
| REC-001/W4 | Partial/full/pending ledger and correction/reopen persistence | Enabled supported actions and per-obligation/currency balances |
| SEC-001/Tests 2/4/6/10 | Ownership/safe downloads/output contracts | No-promise/injection/language regression and stored-XSS browser monitoring |
| P2-01/04/09 | Idempotency, duplicate storage policy, real DB races | Stable retry keys/click protection, duplicate and real two-tab UX |
| P2-12/13/15 and W1 | Draft/account/session privacy, real reset acceptance evidence | Account-bound remount recovery, reset reuse/error UI, user handoff |
| P2-02/03/05/06/07/10/11/14/16 | File/route/response/transaction bounds and service tests | Input limits, processor/provider/React retry tests; preserve passing paths |
| P3-01/02/04/05/07/08/09/10 | Authoritative clock/history/factual projection | Multi-promise agenda/diff/complaint/dashboard rendering, full reconciliation |
| P3-03/06; W5/W7 | Durable notifications, delete jobs/cleanup, PDF/ZIP/timestamp endpoints | Notification preferences, calendar/download/delete/verification interfaces |
| W6 | Private ingest/original-byte/auth envelope | PDF/EML/MSG/OCR/audio text processing and language evaluation |
| W8 | Versioned official-source escalation data, receipt totals | Reviewed next-step guide, drafts and personal counter |
| W9/W10 | Inbox/webhooks/aliases/storage/extension pairing/audio jobs | PWA/share/Chrome extension/upload/transcription adapters and review |
| W11/W12 | Authorized retrieval/credentials/send receipts/reply ingestion | Grounded answers/citations, confirmation drafts and reviewed-send UI |
| W13 | Aggregate privacy/withdrawal, thresholds, operations | Honest sample/method display, source verifier/counters and demo |

## Git and release rules

Rechecked while updating this plan: remote main `893b804`; account branch `888722d1456380d4c5a370d15f49b7b9ee0d0c16`; PR #4 still open/draft. Recheck before starting. Both branches must include that account head or its verified newer merged successor. Do not base on stale feature/frontend/backend branches or merge draft #4 merely to start. Preserve Firebase, private GCS/Cloud SQL, AUTH_SECRET and user-selected 6–128 policy.

1. Publish a **handoff-only baseline** containing these local docs, copied reports and probes, without reset/stash-loss or product changes. It is not yet on GitHub. Coordinator makes a reviewable handoff commit on a `codex/qa-handoff` branch descended from the account branch and shares its SHA. Existing uncommitted auth handoffs must be included/preserved deliberately. No blind `git add .` including private storage, logs, DBs or credentials. This short source-distribution step is not a backend-first implementation phase; each owner can use a verified copy of the same files meanwhile.
2. Akshit uses a separate clone/worktree and `codex/platform-reliability`; Tushar uses another and `codex/intelligence-product`. No two people/chats write in one working tree. Branch names are proposed, not already created. Never overwrite existing matching branches.
3. Small owned-file commits preserve authors. Open draft PRs against the agreed handoff/account-aware base; document stacked base until #4 lands. Carry ancestor work once; do not squash someone else's changes or cherry-pick duplicates blindly. Rebase/retarget only after ancestry checks. No teammate messaging or merges implied by this plan.
4. Each owner runs its own baseline, desired-behavior regression and contract suite. B supplies an optional job/CI script under its owned folders; A incorporates it into root CI. A supplies isolated DB/server fixtures. Local contract tests cannot replace combined real service checks.
5. A assembles a temporary `codex/qa-integration` branch from both reviewed heads. Run all original backend/AI/frontend/integration suites plus desired-behavior regressions, real PostgreSQL concurrent tests, build, stored-XSS browser checks and controlled live provider checks. B verifies UI/AI behavior on this branch. Resolve conflicts in the owning branch rather than silently editing another owner's code on integration.
6. Record exact head/base SHAs, applied migration version, model/config identifier, fixture IDs, request IDs, elapsed time, results and live revision. Never log reset links/OAuth/MFA secrets/raw private evidence. Back up before schema rollout; stage and review rollback before any production update. Do not deploy the integration branch merely because its name contains “integration.”

## Definition of done

A track can be **independently implementation-complete** against the contract while joint integration/live-provider acceptance remains pending. A feature is **accepted** only after real connected checks and required provider steps pass. Preserve original reported verdicts beside dated retests and exact scope. A timeout fix is not proven until the previously blocked semantic test completes through save/reload. Reset/2FA tests need genuine controlled accounts. New cloud services, public aggregates and communications require their applicable authorization; prepare all independent work first.

No new feature implementation or task delegation is requested by this planning edit. Deliver these instructions to the two people; do not launch two agents or create chats on their behalf automatically.
