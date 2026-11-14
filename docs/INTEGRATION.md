# Four-developer integration checkpoints — 24-hour MVP

## Ownership and branching

Ownership is defined in ARCHITECTURE.md. Each developer works on an independent local clone and branch (`codex/frontend`, `codex/backend`, `codex/ai`, `codex/integration` suggested), never a shared filesystem. Branches do not need to exist yet. Integration lead reviews contract changes before other developers adopt them. Each developer brings only owned files; coordinate dependency manifests, root configuration and migrations before editing. No root config changes are approved by this milestone. Integration lead handles reconciliation in docs/tests/scripts; module owners resolve conflicts in their own code. Contract changes must update examples and fixtures together.

## Checkpoints

| Target elapsed time | Checkpoint and evidence |
|---|---|
| 0–2 hours | All four agree field names, enums, routes, directory ownership and decisions below. Backend confirms auth identity and environment names. Frontend uses synthetic snapshots; AI uses exact adapter inputs. |
| 2–6 hours | Backend and AI owners agree import/function signatures and run a stub extraction. Frontend and backend compare create/detail/upload/error payloads. No live AI dependency needed. |
| 6–12 hours | Upload → private evidence → pending review → explicit approval works end to end. Assert no commitment exists before review. Confirm original evidence download authorization. |
| 12–18 hours | Revision preserves original row/links; stale review fails; overdue and resolution match fixed-clock fixtures; complaint preview uses reviewed facts. |
| 18–24 hours | Integration lead runs the minimal plan with owners on staging; record results, commit IDs and blockers. All owners agree one contract revision before demo. |

These are planned later implementation checkpoints, not work implemented in Milestone 1. No commit/push/deployment is performed here.

## Decisions requiring human agreement

1. Confirm four people and exclusive directory ownership, particularly backend/ai as the AI boundary.
2. Confirm backend/frontend runtimes, PostgreSQL deployment, session login integration and same-origin hosting. Authentication must be available before private evidence is deployed.
3. Choose AI provider/model and approve sending selected evidence text to it; stub remains default during integration tests.
4. Choose persistent private local volume versus S3 and assign secret/storage operators.
5. Accept MVP limitations: text/PDF text layer only, no OCR, one-file uploads, unpaginated lists, no automatic sending, no reopen/edit/delete endpoints; timestamps ambiguous in evidence require user review.
6. Accept proposed enums, money units, optimistic case versioning, revision history, and resolution meaning all active promises are fulfilled.
7. Supply or locate the referenced shared AI coding rules. None was present in the inspected repository; these artifacts cannot claim compliance with an unavailable rules document.


## Automated regression suite — 14 November 2026

Tests and runner: `tests/regression/README.md`, `tests/regression/RESULTS.md`, and `scripts/run_integration_regressions.py`. This work adds tests only; no production code, contracts, manifests, branches or Git refs were changed.

Latest inspected remote heads were backend `02e1b4b0a7c3cd2fec57b0bb66e69b9709b809c3` and AI `9ec0eda8af8564b28a49bcedb2a506c61fdcba10`. API/AI contracts match the integration baseline `70f2db0b16c06160a176155c7faa19e555c371ce`. Testing used credential-free source snapshots assembled in /tmp; this integration checkout still has no backend/AI modules.

Run with an isolated Python environment and `python scripts/run_integration_regressions.py --source /absolute/source/root`. Protected HTTP workflows are pending until a backend-owned test authentication hook supplies session/CSRF bootstrap (`--auth-hook /absolute/tests/auth_hook.py`). Explicit `--diagnostic-anonymous` exercises current routes using temporary local SQLite/storage and proves no authenticated behavior. Real RapidOCR reads generated PNG pixels; AI inference uses deterministic mock only. External network calls are blocked. No live Meta success is claimed.

Actual regression results: local checkout **4 passed, 24 pending**; pinned combined sources/default mode **7 passed, 2 failed, 19 pending authentication**; combined sources/anonymous diagnostic **8 passed, 20 failed**. The fixed missing-Meta-credentials adapter path passes. Real standalone OCR and revision history preservation pass. Diagnostic failures remain for HTTP OCR invocation, second-evidence quote association, invented candidates, negative amounts, duplicate evidence IDs, malformed extraction schemas, anonymous evidence access, and top-level errors. Known defects are failing assertions, not xfail. See RESULTS.md for counts and limits.

Next integration checkpoint: Lokesh/Kunal provide their next source snapshots and an agreed test-only auth hook; rerun the same assertions without weakening them. The screenshot test is the explicitly requested AI Milestone 2 extension; the current API upload contract still lists only text/PDF, so formal screenshot contract adoption remains a human agreement item. No contract was modified here.


## Latest commit re-audit — backend ac3a916 / AI 1b05140

Exact snapshots: backend `ac3a916936e2ed551e7e5f5a7b60e61300da674e`, AI `1b0514002f4535baf2544c5fa505b169065e00cb`. Retrieved by read-only connector and combined only in /tmp after blob verification. Production files, contracts, original 28 regression assertions and original runner are unchanged. Full evidence: `tests/regression/RESULTS.md` and `tests/regression/reaudit_support/results.json`.

**FAIL: integration remains blocked.** Strict acceptance: **6 PASS / 3 FAIL / 19 PENDING** because no valid authenticated session can be established. Separate unverified-session diagnostics of all 28: **15 PASS / 13 FAIL** (old diagnostic baseline: 8/20). Complete backend suite: **31 PASS / 19 FAIL**; complete AI suite: **26 PASS**. Six supplementary security probes all FAIL. Nine old failing assertions now pass diagnostically; two previously passing adapter assertions regressed due to a new TypeError.

Anonymous evidence upload/download now rejects missing credentials, but any nonempty random cookie/bearer token is accepted. Cases have no owner_id, anonymous case GET/POST and direct commitment creation still succeed. Hardcoded/test tokens and cookie presence were not accepted as authentication proof. Two-user authorization and all genuinely authenticated workflows remain PENDING until identity/session validation, ownership and CSRF are implemented. No production auth dependency was bypassed in diagnostics.

Real loopback HTTP screenshot attempt: anonymous upload 401, forged-session upload 201, extraction **422 UNREADABLE_EVIDENCE**, **0 real OCR calls / 0 mock AI calls**, review PENDING because no draft exists. Independent real RapidOCR tests pass; the HTTP integration does not.

Required module-owner fixes: backend calls the actual AI file_source interface and translates CommitmentExtractionResult instead of assuming an evidence-list/dictionary API; wire DocumentProcessor instead of importing absent ai.ocr; validate extraction schemas before persistence and duplicate evidence IDs before invoking AI; implement verifiable sessions, CSRF and per-user ownership throughout domain routes. Candidate membership/negative amounts and tested top-level error envelopes now pass with synthetic draft/error injection; revision/original evidence retention remains passing diagnostically. Integrated quote attribution and missing-Meta-credentials handling cannot pass until the TypeError is fixed. No real Meta request or deployment/PostgreSQL readiness claim was made. Stop after this re-audit; fixes remain with module owners.
