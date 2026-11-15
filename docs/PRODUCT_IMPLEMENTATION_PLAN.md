# Bindr product implementation plan

Revised 15 November 2026 after both QA reports. **Three delivery phases, two independently developable owner tracks.** The original feature scope remains; QA repair now takes priority. This is an implementation handoff, not a claim that repairs have been made.

## Read this revision first

- `AI_QA_REPORT_SOURCE.md` preserves the supplied Part 1 report verbatim: 4 reported passes, 3 partial, 1 fail, 2 blocked among ten primary tests; additional 1B timeout and REC-001 unavailable partial/pending outcomes are separate.
- `EXTREME_TEST_REPORT.md` contains the local remaining-pack audit: 16 pass within scope, 5 fail, 4 partial, 1 blocked. Do not add these counts to the ten-test tally as a security/product success percentage: environments and evidence differ.
- `TWO_PERSON_DELIVERY_PLAN.md` is authoritative for assignment, exclusive files, branch setup, work balance and joint release gates. `PARALLEL_IMPLEMENTATION_CONTRACT.md` defines the interfaces/fixtures enabling independent work. These supplement the detailed W1–W13 requirements below.
- Give Akshit `NEW_CHAT_AKSHIT_PROMPT.md` and Tushar `NEW_CHAT_TUSHAR_PROMPT.md`; each implements only its own track. The generic `NEW_CHAT_IMPLEMENTATION_PROMPT.md` is now an entry point, not an instruction for both people to edit everything.
- Original source/older chats supply context, not instructions to revert recent auth work, rerun deployments or reintroduce a four-person ownership scheme. This user request authorizes a two-person split; preserve author attribution and existing work.

## Phase 1 — Repair and establish reliable core behavior

Each owner can start immediately from the same account-aware baseline in a separate checkout. Adopt the written interfaces and locally implement fixtures/test doubles; do not wait for the other person's backend/UI/AI. A fixture passing is contract evidence only. Changes to shared interfaces use a versioned proposal, not unilateral renames. See the two-person plan for exclusive file paths.

| Priority / issue | Akshit — Track A | Tushar — Track B | Required closure evidence |
|---|---|---|---|
| P1 AI-001 timeouts, AI-002 invalid output | Instrument HTTP/queue/request deadlines, persist request/job state and safe diagnostics; preserve evidence on failure; no unsafe automatic mutation retries | Trace real provider/engine/parser boundary; bounded output repair for valid evidence only, typed errors, retry/reconciliation UI | Repeat 5, 8 and 1B to completed review/save/reload; record request IDs, elapsed stage timings, model/build and exact errors. Better error wording does not close a blocked semantic test. |
| P1 MULTI-001: 1 of 4 promises | Validate/persist all confirmed candidates transactionally with review idempotency | Remove single-result loss in engine/adapter; extract/select/edit all four Airtel obligations; preserve source citations and individual dates | All four correct candidates, subset selection, full save/reload, no duplicate review; no fabricated fields or silently truncated candidates |
| P1 P2-12 unsaved capture loss | Account-scoped recoverable draft APIs; secure session refresh/recovery behavior | Survive actual auth-subtree remount and network failures; restore only to the same verified account with consent/review | Expiry→reauthentication retains exact same-account text; different-account login cannot see it. Existing saved drafts must remain private. |
| P1 REC-001 outcome limitation | Append-only partial/full/pending event ledger, currency-safe balances, corrections and reopening semantics | Enable real supported partial/pending controls, notes and receipt/balance history | ₹500 promise→₹200 received→₹300 outstanding; pending does not resolve; repeated save idempotent; reload/device persistence; full receipt checked separately |
| P2 P2-01/P2-04 duplicates; P2-09 race coverage | Create/review idempotency and identical-PNG policy, atomic PostgreSQL conflict behavior | Stable operation keys across uncertain retries, click guards and duplicate review affordances | Same operation returns same result; same key/different payload conflicts; intentional separate cases remain possible; real two-tab + PostgreSQL overlap checks |
| P2 DATE-001, P2-08; blocked Test 8 | Persist communication date/provenance; deterministic validated deadline service with holiday/version policy | Visible impossible/future communication-date warnings, exact date/source wording, unknown anchor/conditional states; no silent normalization | Nov 31 remains invalid with warning; 2099 communication date follows explicit warning policy; 28 Dec +5 calendar days =2 Jan only when anchor confirmed; exact stored timezone/date verified |
| P2 REV-001, Tests 1/9/1B | Append-only history and explicit company revocation event; never erase obligations automatically | Source-linked conflict/revision/cancellation proposals and visual diff | Canonical Test 1 proposes latest explicit Nov 20, preserves Nov 15 and earlier-mentioned Nov 18 with explanation; user can confirm/override. Test 9 shows historical revocation, no unqualified new active refund. Save/reload history inspected. |
| P1 security coverage SEC-001 | Original download headers, safe stored data/API output, no sensitive logging | Execute stored-XSS regression across review, saved detail, evidence, activity, complaint/notification preview/export | Save/reload exact Test 10 fixture with browser execution monitoring: no scripts/event handlers/remote loads; Unicode/source text retained. Static screenshot alone is insufficient. |
| Acceptance gaps P2-15, P3-03/05/06/10 | Dedicated auth reset checks, deletion/jobs, authoritative projections | Real reset invalid/reused-link states, multiple-obligation UI, dashboard and delete flows | Controlled inbox first-use/reuse + existing-session revocation, actual notification cancellation, live dashboard reconciliation; unavailable providers remain blocked, not waived |

Record report-derived versus reproduced findings separately. No raw Part 1 provider output/build trace was supplied; the test pack provides canonical inputs but does not reconstruct missing original outputs. Keep original reports immutable. Retest reported passes 2/4/6/10 as regressions; do not assume payload-specific prompt-injection or mixed-language success generalizes.

**Phase 1 exit:** the core repair subset of W1–W4 plus required draft/notification/delete foundations is connected and demonstrated; unresolved release-critical failures or required blocked semantic/security checks prevent sign-off. Finish remaining Phase 2/3 implementation independently if an external account is unavailable, but do not claim Phase 1 accepted. Akshit owns transport/data/security service checks, Tushar owns engine/UI semantics/rendering checks, both sign integration evidence.

## Product outcome and scope

Make Bindr a dependable way to capture a company's promises, confirm what they mean, notice when terms change, track actual fulfillment and prepare the next action with the original proof attached. Preserve the core loop: **evidence → AI suggestion → human confirmation → tracking → user-confirmed outcome**.

Phase 1 above repairs known defects and closes core evidence gaps. Phase 2 completes the dependable case workflow; Phase 3 adds easier capture, intelligence and integrations. Work packages below retain their IDs for traceability; parts already completed during repair must be reused rather than implemented twice. The two-person assignment applies in every phase.

The source proposal is a requirements input, not an accurate audit of today's implementation. In particular, Google login is already live, existing cloud drafts/preferences should be reused, and hashes already exist. A hash or timestamp cannot establish that a company's alleged message is authentic or legally admissible.

## Starting state: verify again before editing

| Item | Last verified state |
|---|---|
| Active local checkout | `bindr-google-cloud`, inside the project directory. `bindr-app` is an older sibling checkout; do not accidentally implement there. |
| GitHub repository | https://github.com/akshitbhargav87-svg/Bindr |
| GitHub main | `893b80426fd7ddf4e308aa2532c9f49891a61b12`, checked through the GitHub API while preparing this plan. |
| Account branch | `codex/account-auth`, head `888722d1456380d4c5a370d15f49b7b9ee0d0c16`. It contains the deployed account implementation. |
| Account PR | https://github.com/akshitbhargav87-svg/Bindr/pull/4 — open, draft, mergeable at the last check. Do not start from main and lose the login work. |
| Account CI | Latest recorded run passed: https://github.com/akshitbhargav87-svg/Bindr/actions/runs/43648609167. Recheck after any changes. |
| Hosting/data | Existing Google Cloud project `project-0021b03b-28bd-43e6-9d4`, region `asia-south1`; Cloud Run, Cloud SQL PostgreSQL, private Cloud Storage, Secret Manager. |
| Live deployment | Revision `bindr-00003-cm9`, image `888722d14563-20261114230005`; a Cloud SQL backup completed before deployment. |
| Live URLs | https://bindr-404714938412.asia-south1.run.app and https://bindr-tor2633xpq-el.a.run.app |
| Account facts | Google sign-in succeeded, independently observed in the workspace/settings. The verified account and session survived reload. Cloud preferences saved, survived reload and were restored. |
| Remaining account checks | Real email registration/verification, password reset, TOTP enrollment/challenge, two-account isolation and authenticated cross-device case/draft checks are still pending. Do not report them as passed. |
| Password requirement | The user explicitly chose 6–128 characters. Preserve it and Google's configured policy validation. |
| Email restriction | Firebase currently refuses template edits even for an Owner. Default Firebase verification/reset handlers remain configured. This is not an IAM Owner problem and must not restart project setup. |
| Access | Both Akshit and Tushar now have project Owner access. No passwords or private keys need to be shared in chat. |
| Local handoff changes | `docs/AUTHENTICATION.md` and `docs/RESUME_ACCOUNT_AUTH.md` have uncommitted updates from the deployment chat. The source, this plan and the new-chat prompt are also local planning files until committed. Preserve them. |

Read `RESUME_ACCOUNT_AUTH.md` first for the latest detailed release evidence. All snapshot values above are dated, not assumptions about the next chat's current state.

## Initial repository and history audit

1. Read the 5–6 prior project-chat Markdown transcripts if supplied, oldest to newest, including decisions, corrections and the final stopping points. If chat tools are available, find the actual related project chats and read their turns; a sidebar title/summary is not a full history review. Do not claim to have read inaccessible conversations. Extract a short decision log instead of repeatedly rereading the entire history.
2. Inspect the working tree, actual Git root, remotes, branch ancestry, GitHub branches, PR #4 and current checks. Read local uncommitted files before switching branches. Resolve a safe feature-branch base that includes the account work; preserve original author history. Do not merge the draft account PR merely to obtain a convenient base.
3. Trace the complete real request path, not just components: capture → upload/storage → document processing → AI adapter → extraction review → commitment/revision → case state → complaint/export → account ownership. Read the tests and deploy scripts as well as the README.
4. Compare every feature below with the connected implementation. Label it **verified**, **implemented but unverified**, **demo only**, **missing**, or **externally blocked**, with file/route/test evidence. Older architecture/handover documents explicitly describe historical states and cannot establish present behavior.
5. Capture a fresh baseline using the actual CI commands. Record failures that predate the work. Establish a practical implementation checklist in `docs/IMPLEMENTATION_STATUS.md`, including decisions, migrations, exact test commands/results, release commit, live revision and the next action. Do not spend the whole first turn writing another roadmap: proceed into the first vertical slice after the focused audit.

### Code areas to inspect and extend

| Concern | Existing locations |
|---|---|
| Persistence and ownership | `backend/app/models/`, `backend/app/core/database.py`, `backend/app/core/auth.py`, `backend/app/services/account_auth.py` |
| HTTP contracts and mutations | `backend/app/schemas/contract.py`, `backend/app/api/endpoints/{accounts,cases,evidence,extractions,commitments,timeline}.py`, `docs/API_CONTRACT.md`, `docs/AI_CONTRACT.md` |
| AI/OCR and source validation | `backend/app/services/ai_adapter.py`, `backend/app/ai/{engine,schemas,prompts,document_processor}.py`, `backend/app/ai/providers/` |
| Connected frontend | `frontend/src/api/`, `frontend/src/state/`, `frontend/src/pages/`, `frontend/src/components/` |
| Existing demo logic | `frontend/src/api/mock-mutations.ts`, calendar/capture/case helpers. Useful behavior references; not proof that production supports a feature. |
| Design | Current `frontend/src/components/ui.tsx`, shared CSS, workspace/capture/communication/outcome/export screens. Historical `design/` briefs and Mobbin references provide context; the latest actual design and user corrections take precedence. |
| Verification and hosting | `backend/app/tests/`, `backend/app/ai/tests/`, `tests/regression/`, `frontend/checks/`, `.github/workflows/ci.yml`, `scripts/`, deployment/authentication docs |

## Phase 2 — Complete the dependable case workflow

Implement these work packages in the order shown, delivering connected backend, frontend and tests together. W1–W8 are work packages inside this phase, not additional phases.

### W1. Stabilize accounts and introduce real schema migration support

- Finish or obtain evidence for the outstanding live account checks. Use two synthetic accounts for isolation. Provider-stubbed tests remain useful but do not prove real email, OAuth, TOTP or cross-device behavior. Personal credentials and authenticator enrollment are user-operated steps.
- Verify saved drafts, preferences, original downloads, global logout/session revocation and one-time legacy-workspace attachment. Old anonymous cookies are hostname-specific: test attachment from the hostname where the original cookie exists. Never transfer records based only on an email address.
- Preserve Firebase/Identity Platform, Cloud SQL and private GCS. Do not replace the account system, move data to another provider, lower existing session protections or redesign login unnecessarily.
- Inspect migration tooling before changing the schema. The current database helper has SQLite-specific additive patches; that is insufficient for modifying existing PostgreSQL tables. Introduce a small versioned migration system, such as Alembic if appropriate, with a baseline for the existing database, explicit PostgreSQL/SQLite handling, safe defaults and a documented upgrade/rollback strategy. Do not rely on `create_all` to add columns.
- New columns start nullable or receive honest defaults. Existing evidence gets **unknown communication date**, not upload time disguised as a message date. Test an upgrade from a populated old database, with existing sessions, case history, original hashes and drafts intact. Back up before production migration and avoid incompatible application/schema rollout ordering.

### W2. Communication dates, deadline resolution and manual fallback

- Persist each evidence item's communication date/time, timezone, precision (date only versus exact time), provenance (message metadata, extracted suggestion or user confirmation), original wording and corrections with reasons. Record import/upload time separately. A message can contain promises with different anchors; do not force every commitment to use a single case-level date.
- Introduce a server-owned deadline service. Cover explicit dates, calendar days, business days, ranges such as 5–7 business days, explicit times, month/year boundaries and an unavailable reference date. Preserve earliest/latest dates, the anchor, timezone, counting rule, holiday calendar/version and a readable explanation. Keep an explicit user-confirmed override distinct from the computed proposal.
- Default to the existing Asia/Kolkata convention where appropriate, with visible assumptions. Do not silently apply a regional holiday list to everyone. Provide an explicit weekend/holiday configuration, verified calendar sources and an honest weekend-only fallback when holiday coverage is unavailable. Once confirmed, historical calculations must remain reproducible after calendar data changes.
- For ranges, display the expected window; crossing its earliest date is not automatically overdue. Overdue follows the confirmed final deadline and actual fulfillment. Unknown dates stay undated. AI extracts language and uncertainty; deterministic server code does arithmetic.
- Flag conditional/vague wording, uncertain OCR and missing anchors for review. These are explanations, not invented confidence percentages or legal judgments about whether a promise is enforceable.
- Add a production manual-entry route through the same ownership, CSRF, versioning and review rules. Use an explicit manual origin and user confirmation; do not invent an extraction ID, AI quotation or unsupported evidence link. It must work when AI is unavailable, rate-limited or finds nothing. Allow an honest user-attested record if no source exists, visibly distinguished from source-backed evidence.
- Acceptance: a Friday message with a business-day range has the correct window under the selected calendar; missing dates are not inferred from upload; edits/reloads preserve provenance; stale writes fail cleanly; an AI outage still permits a saved manual record.

### W3. Multiple promises and automatic revision/contradiction suggestions

- Reuse the existing candidate-list review contract where possible: it already accepts multiple candidates, while the real adapter primarily extracts one promise per file. Extend the model/provider boundary and document chunking without creating a parallel extraction pipeline.
- Extract all distinct supported candidates within explicit bounded limits, each with stable candidate identity and exact evidence/page/message references. Deduplicate repeated content and quotations. Allow selecting a subset, editing each candidate, choosing its source/date and confirming new/revised items transactionally. Be explicit about whether unselected candidates are rejected or remain reviewable.
- Compare each proposed promise with relevant active promises from the same owned case. Consider company, order/reference, kind, amount/currency, fulfillment subject and communication chronology. Separate corroboration, revision, contradiction, unrelated promise and insufficient evidence. Unknown chronology and vague language must not become confident contradictions.
- Show a side-by-side diff of old/new dates, amounts and wording, with both original source links and an explanation. The user accepts, changes the predecessor or keeps a separate promise. Never supersede automatically merely because a case has an active promise.
- Preserve predecessor rows and original evidence. Prevent stale predecessor selection, cross-case links, replayed review, duplicate confirmations and branching revisions that violate the chosen history model. A change to the deadline must invalidate or reschedule dependent reminders and mark stale complaint drafts for review.
- Acceptance: one email yields two independently selectable promises; an unrelated new obligation is not classified as a revision; a changed refund date generates a supported diff; only human approval changes the active record.

### W4. Actual outcomes, notes and case lifecycle

- Add persistent outcome events for partial receipts, full receipt, still waiting and a company's claim that payment was processed. A company claim is not a user-confirmed receipt. Store source references, the recorded date and who attested to it.
- Maintain a ledger per obligation/currency, using integer minor units. Derive received/outstanding totals from user-confirmed events, handle non-monetary partial fulfillment, and require a deliberate full-resolution action. Prevent accidental double counting, negative receipts, currency mixing and invalid allocations after a revision. Corrections/reversals retain an audit trail.
- Add reopen, archive/restore and company/title correction with reasons. Reopening preserves earlier outcomes; it must not erase receipts or silently reset the amount received. Decide and test which obligations become active again. Archive hides a case without pretending it is fulfilled.
- Add dated notes/annotations and clearly distinguish original text, AI proposals, user notes and company claims. Notes describing a phone conversation are user testimony until supported by an actual recording or written confirmation.
- Update overview, agenda, history, complaint drafts and exports from the same server facts. Never let a client-only balance disagree with production.
- Acceptance: a partial refund leaves the right balance overdue, a processed-payment message does not resolve it, and reopen/archive/restore retain the complete history across reload/device changes.

### W5. Reminders, calendar export, case health and follow-up scheduling

- Add opt-in email reminders first, plus authenticated `.ics` export. Support configurable defaults at 3 days, 1 day and the due day, a clear timezone/send time and sensible handling for deadlines created too late for earlier offsets. Avoid duplicate reminders for the same obligation/revision.
- Introduce a durable job/outbox design using the existing database and appropriate managed Google Cloud scheduling/queue services after checking current documentation. Cloud Run can scale to zero; browser tabs, process-local timers and an in-memory scheduler cannot guarantee background delivery. Keep job handlers authenticated and least privileged.
- Persist scheduling/delivery state, retries, provider message references, failure reasons and idempotency keys. Recheck the latest case version, confirmed deadline, outcome, account and preferences immediately before dispatch. Superseded/resolved/deleted/archived records must not produce stale messages. Handle ambiguous provider timeouts honestly rather than promising impossible exactly-once delivery.
- Calendar output uses stable UIDs and correct timezones/ranges; a static downloaded event does not magically receive subsequent changes. If adding subscriptions, make their access revocable and explain their privacy model.
- Add Web Push as an opt-in channel, including permission-denied/device-not-supported states. WhatsApp delivery is completed with its integration in Phase 2. Settings exposes real channel status; an unavailable provider must not show a working toggle or a fake successful send.
- Add an explainable case health indicator: missing information, on track, nearing deadline, overdue or resolved, derived from confirmed facts. Add a user-controlled “if no reply in N days, remind me with a stronger draft” schedule. It creates a prompt/draft; it does not silently send messages.
- Acceptance: scheduled dispatch survives service restart/scale-to-zero, a deadline revision cancels the old reminder, partial balances appear correctly, opt-out stops deliveries, retries do not cause uncontrolled duplicates, and one real configured transport delivers a synthetic reminder.

### W6. Better imports and multilingual processing

- Add page-level OCR fallback for scanned and mixed PDFs. Preserve original bytes and page references, reuse the OCR boundary, and avoid re-OCRing good text unnecessarily. Bound page count, processing time, memory, attachment recursion, file sizes and per-account quotas; use jobs/progress for work that exceeds a normal request.
- Support `.eml` and `.msg`: preserve the original message, extract sender/recipient/date/subject/body, handle quoted threads and bounded attachments, and distinguish claimed headers from authenticated provenance. Sanitize HTML and do not load tracking pixels or remote resources. Apply existing upload/authorization controls to extracted attachments as well.
- Add reviewed fixtures for Hindi, Hinglish and at least one explicitly identified additional regional-language path. Preserve source-language quotations; a translation is separately labeled. Evaluate OCR and extraction independently with native-script, mixed-language, ambiguous and low-quality examples. Do not advertise support for every Indian language based on English-only tests.
- Acceptance: a mixed scanned/text PDF, an email with an attachment and realistic multilingual messages produce usable source-linked proposals; corrupt/oversized/encrypted/unsupported input receives an honest recoverable error and manual-entry option.

### W7. Portable evidence, privacy controls and integrity verification

- Produce a readable, paginated PDF with case identity, dates/timezone assumptions, confirmed promises, original/revised comparisons, outcome ledger, source quotations, page/message references, notes, unresolved issues and a clear export/version timestamp.
- Provide a single downloadable evidence ZIP containing that PDF, the exact original files, a machine-readable record and a SHA-256 manifest. Some originals cannot be meaningfully embedded as PDF pages; do not call a screenshot/preview a byte-identical original. Include selected previews in the PDF and actual originals in the bundle. Explain that someone the user shares the downloaded bundle with can read its contents.
- Tie output to a consistent case snapshot/version. Include warnings for missing evidence and unconfirmed facts; refresh review when facts change. Keep generated bundles private with bounded retention and authorization checks.
- Add case export, account-wide data export and deliberate case/account deletion. Define confirmation, recent-auth requirements, active-session revocation, job cancellation and idempotent cleanup of SQL rows, GCS originals, generated exports, provider connections and credentials. Hide a deletion-requested account immediately while retryable cleanup finishes. Document actual backup/log retention and third-party-copy limits rather than promising immediate erasure everywhere.
- Keep original evidence immutable during retention, while honoring explicit owner deletion. One test account cannot export/delete another's data, and public download URLs must not bypass account checks.
- Reuse existing file hashes, add a local/offline manifest verifier and an optional trusted timestamp integration. Record the difference between a Bindr receipt time and an externally attested timestamp. A verification QR opens a verifier, not a public private-case URL. Never claim hashes/timestamps prove authorship, truth, legal certification or court acceptance.
- Acceptance: a reviewer can recompute original hashes; alteration is detected; PDF source references are correct; exports cannot cross accounts; a disposable account's delete workflow completes across storage and queued jobs without deleting another account's records.

### W8. Recovery tools and a complete core demo

- Add an escalation guide based on confirmed facts and the user's issue/jurisdiction/payment method. Research current official procedures before publishing routes, deadlines or eligibility. Version sources and their verification dates; avoid hardcoding unverified grievance contacts.
- Provide reviewed follow-up/grievance/dispute drafts, prerequisites, an evidence checklist and relevant official destination links. Never invent a legal deadline, suggest every route fits every case, promise recovery or automatically file. Explain the informational nature without turning the interface into a wall of warnings.
- Add a personal money-received counter based on the outcome ledger, with reversals, per-currency totals and a distinction between reported receipt and money demonstrably recovered because of Bindr.
- Prove the full journey with synthetic data: capture a dated source with two promises → accept a calculated date → add a changed promise → accept the diff → record a partial receipt → deliver a reminder → prepare an escalation draft → export original evidence → confirm the rest/reopen if appropriate.

**Phase 2 exit:** this journey works in connected mode with safe migrations and private account data. Existing auth/storage/extraction/history behavior remains intact. Each missing real-provider or user-operated check is explicitly recorded; the phase is not labeled fully accepted while a required check is still unverified.

## Phase 3 — Frictionless capture, case intelligence and connected actions

Build on the earlier ingestion, provenance, jobs and outcome APIs. Owners develop against the versioned contract fixtures independently, then integrate; do not duplicate business rules inside connectors.

### W9. Forward-to-case email, phone sharing and WhatsApp

- Provide revocable, unpredictable per-case/per-account inbound email aliases. Verify inbound-provider webhooks, bound message/attachment size, deduplicate provider events and message IDs, rate-limit abuse and quarantine suspicious/unmatched messages. Possession of an alias is not permission to read case data. Imported content enters an inbox/review queue, not an automatically confirmed promise.
- Match a message to a case using references/participants and existing context; ask the user when ambiguous. Preserve the raw email, parsed fields and import event. Forwarded headers are not proof that the original sender is genuine.
- Add a mobile-friendly PWA/share target where supported, with an accessible upload/paste fallback. Accept shared screenshots, files and text, let the user select a case and communication date, and use the same human review flow. Do not imply direct access to a user's personal WhatsApp inbox.
- Add approved WhatsApp capture/notification capability through the appropriate supported platform/provider, with verified webhooks, account linking, opt-in/out and current provider/template requirements. Keep “share from WhatsApp to Bindr” separate from “Bindr reads WhatsApp chats” and “Bindr sends a WhatsApp reminder.”
- Acceptance: forwarding a duplicate email creates one intake item, guessed/revoked aliases cannot access cases, sharing a screenshot works on supported phones, unsupported browsers have a working fallback, and a real configured WhatsApp path is verified before being advertised.

### W10. Browser capture and recorded calls

- Build a minimal Chrome extension using current extension guidance. Capture a support-chat selection/screenshot only after an explicit user action, show a preview, choose the destination and submit through a purpose-built authenticated/short-lived pairing flow. Do not expose the application's HttpOnly cookie or copy long-lived account credentials into the extension.
- Avoid broad always-on host access or silent monitoring of unrelated browsing. If offering live promise detection, make it a visible opt-in for the selected page, process only the needed chat content and require confirmation before capture/upload. Document browser store/installation requirements and fallback behavior.
- Support uploading an existing call recording, preserving original audio, transcript segments and timestamps. Use a configured transcription provider and language support that is actually tested. Display uncertain speaker attribution and transcription separately from the source audio; do not pretend a note is a recording. Explain consent/recording requirements appropriate to the intended jurisdiction after current-source verification.
- Connect transcript-linked proposed promises to the existing review flow. No live/background microphone recording is necessary for this feature.
- Acceptance: an explicitly captured chat and an uploaded call both yield traceable review candidates; an unpaired extension cannot access cases; a user can play the exact audio segment behind a cited promise.

### W11. Ask your case and get it in writing

- Add retrieval over the currently authorized case's evidence, confirmed facts, notes and transcripts, with page/message/audio citations. Enforce ownership before retrieval; untrusted evidence cannot issue tool instructions. Separate confirmed facts, company statements and user notes in answers.
- Require grounded citations, support an “insufficient evidence” answer, and do not fabricate an amount, deadline, quotation or legal conclusion. Recheck current case version and handle deleted/revoked evidence. Evaluate question answering on an adversarial fixture set, including two-account/cross-case leakage and prompt injection.
- Add a “get it in writing” draft from a user-recorded phone promise, explicitly requesting company confirmation. Link it to the underlying note/call. A generated draft or a sent email is not the company's acceptance of its contents.
- Acceptance: “what changed?” answers with both sources; “what did they promise on the call?” links the segment; an unsupported question abstains; source text cannot cause data exfiltration or unapproved sending.

### W12. Gmail sending, reply ingestion and follow-up completion

- Implement deliberate Gmail connection with the minimum permissions needed for the selected capabilities. Check current OAuth, provider verification and production requirements before choosing scopes. Encrypt provider refresh credentials server-side, keep them out of logs, and provide disconnect/revocation.
- Let the user review the exact recipient, subject, body and attachments before sending. Store the delivery receipt/thread reference and ingest replies using verified events or a bounded durable polling strategy. Deduplicate with forwarded email to avoid double ingestion. Emails sent by Bindr remain user correspondence, not company evidence.
- Reuse the follow-up scheduler: no response can schedule a stronger reviewed draft, but a new reply, resolution, deletion, disconnect or opt-out cancels obsolete work. No unsolicited autonomous sending. External test emails/messages require the user's explicit authorization of recipient/purpose/content scope; otherwise prepare drafts.
- Acceptance: a synthetic reviewed message sends through the connected account, its reply appears once in the correct intake/case, credentials are not exposed, disconnect stops future access, and retries cannot cause uncontrolled duplicate sends.

### W13. Privacy-conscious aggregate features and final operational acceptance

- Add an opt-in company promise-keeping scoreboard and optional global money-received total only after defining their data contract. Use canonical company identities, minimum aggregation thresholds, deduplication, abuse/reporting handling and a way to exclude/delete contributions. Define treatment of partial receipts, revisions, open cases and sample-selection bias. No private messages, case links or personal identities in public responses.
- Distinguish observed, self-reported outcomes in participating cases from objective claims about a company's entire customer base. Label the denominator, sample size, period and method; suppress insufficient samples rather than inventing percentages. Handle withdrawal/deletion and aggregation recomputation. Public release depends on an explicit privacy/moderation review; the implementation can remain disabled until that review is complete.
- Complete the optional externally trusted timestamp and any remaining notification channels with real provider evidence. Document transport/provider costs, setup, quotas and operational constraints from current official sources before activation.
- Recheck durable retries, dead-letter handling, account rate limits, resource quotas, monitoring without raw evidence/tokens, cleanup/retention, backups/restore and deployment rollback. Add a repeatable short demo and a failure-path demo; do not use invented benchmarks or recovery claims.
- Acceptance: authenticated features work across devices, scheduled work survives restart, cross-account probes fail, public aggregate responses leak no case data, low-sample results are suppressed, and deleting/withdrawing an account removes its eligible public contribution under the documented process.

**Phase 3 exit:** each connector has a tested adapter, connected user flow, configuration instructions and recorded live acceptance where credentials/approvals are available. Anything externally blocked has an explicit status, a working fallback and the exact remaining owner action. An entire feature is not “complete” merely because its unavailable provider was mocked successfully.

## Complete source-to-work mapping

| Source feature | Work package |
|---|---|
| Accounts, recovery, optional 2FA and cross-device access | W1; regression gates throughout |
| Persisted communication date | W2 |
| Business-day/relative/range deadlines, holidays, weak-wording flag | W2 |
| Production manual fallback from original project vision | W2 |
| Multiple promises per document | W3 |
| Automatic contradiction/revision detection and visual diff | W3 |
| Partial fulfillment, pending, reopen; archive/corrections | W4 |
| Notes, annotations, company claim versus actual receipt | W4 |
| Email/push/WhatsApp reminders and calendar export | W5 and W9 |
| Case health meter | W5 |
| Timed follow-up sequences | W5 and W12 |
| Scanned PDFs, .eml and .msg | W6 |
| Hindi, Hinglish and regional-language processing | W6 |
| Evidence PDF and original-file package | W7 |
| Export/delete my data | W7 |
| Tamper-evident hashes, timestamp, verification QR | W7 and W13 |
| Escalation ladder and reviewed drafts | W8 |
| Personal/global money-received counter | W8 and W13 |
| Forward-to-case email | W9 |
| WhatsApp/mobile share-sheet capture | W9 |
| Browser extension/live support-chat capture | W10 |
| Call audio upload/transcription | W10 |
| Ask your case with citations | W11 |
| Get it in writing generator | W11 |
| Send through Gmail and ingest replies | W12 |
| Company scoreboard | W13 |

## Architecture and implementation rules across all phases

- Extend the existing React/TypeScript/FastAPI/SQLAlchemy/provider-adapter architecture. Add focused services for deadlines, outcome ledgers, exports, scheduling and connectors; avoid a speculative microservice rewrite. Keep SQL as the source of case/account/job truth and GCS as private source storage.
- Evolve shared API/schema contracts with compatible migrations and typed frontend decoding. All owned-resource lookups, async jobs and generated downloads must enforce account ownership; writes retain CSRF, origin and optimistic version checks. Async work carries resource/version references, not a stale unchecked authority grant.
- The AI never confirms facts, changes outcomes, supersedes promises, sends correspondence or files a complaint on its own. All AI input is untrusted source material; validate structured output and citations on the server. Bound document/LLM context and per-account usage.
- Preserve the approved Bindr UI: shared components, current typography, restrained colors, existing source/review/timeline patterns and useful mobile layouts. The user explicitly rejected an unrelated login aesthetic. Inspect the current shared code before introducing new designs; don't add a separate visual theme for every feature.
- Show clear queued/processing/review/failed states; preserve user input on retries, account changes and stale versions. Unsupported channels and unavailable integrations are labeled or hidden. A fake demo success is not a fallback for a broken production provider.
- Choose providers after checking existing account/tools and current official documentation. Finish everything independent first, then ask for the smallest concrete missing setup/credential/approval. Do not request another Owner grant for an already authorized account, ask for private keys in chat, send messages to teammates or silently provision costly services.
- Add focused feature flags/configuration only when they make incomplete external integration safe. Persist flags centrally where needed; do not implement private production data in browser-only demo state.
- Preserve a useful audit trail without logging evidence bodies, email action codes, OAuth tokens or MFA setup secrets. Define data minimization/retention rather than using “fully secure” as an untestable claim.

## Verification and release evidence

Use the repository's actual supported commands and environments. At the time of writing, CI runs:

```text
python -m pytest backend/app/tests backend/app/ai/tests -q
python scripts/run_integration_regressions.py --source . --auth-hook tests/regression/final_acceptance/signed_session.py --ocr-model-dir .ocr-models
cd frontend
npm run check
npm run build
node checks/live-api.mjs http://127.0.0.1:8000
```

The last command requires the appropriately configured real local FastAPI process and connected frontend build; use the CI startup/configuration and required OCR setup rather than running the line in isolation. Keep Windows/local and Linux/CI command differences explicit.

Add meaningful tests for migration of populated PostgreSQL, calendar boundaries/holidays/timezones/ranges, multiple-candidate partial review/replay, false revision matches, ledger/reopen behavior, notification races/retries/cancellation, import limits/HTML safety/multilingual quality, export integrity/private access, full deletion cleanup, connector webhook authentication/deduplication, grounded case answers and aggregate privacy. Use a real test database for constraints/concurrency that SQLite cannot prove. Stub paid providers for deterministic unit tests and record separate real-provider acceptance; neither substitutes for the other.

For each work package, record files/routes changed, migration implications, user-visible behavior, exact check results and any unresolved provider/user step. Use small reviewable commits/PRs on branches that include the preserved account baseline. Do not merge or claim production readiness while required release checks are unresolved. Stage and back up migrations; deploy to the existing service only when the current authorization and release gates cover that change. Verify the actual deployed commit/revision, private originals and saved records after release. Keep the handoff current so a fresh chat can resume without reconstructing every historical tool call.

## First useful implementation session

Use the owner-specific prompt and file boundaries. Akshit starts A1 (migrations, operation idempotency and draft/date foundations); Tushar starts B1 (provider timeout/invalid-output diagnosis and four-candidate extraction), alongside B2's safe capture recovery shell. Both use the frozen contract fixtures rather than waiting for a merged branch. Implement, then independently run component/contract tests; combine branches only for the joint release checks. Read `TWO_PERSON_DELIVERY_PLAN.md` before following any older sequential work-order paragraph above.
