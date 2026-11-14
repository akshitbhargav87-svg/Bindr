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
