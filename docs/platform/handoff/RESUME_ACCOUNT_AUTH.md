# Account authentication handoff — 15 November 2026

## Current branch and implementation

Repository: bindr-google-cloud. Branch: codex/account-auth, originally based on main 893b804. Initial save was 0f79fb9. The resumed review fixed cross-tab account/session races, automatic restoration of saved cloud wording, stale facts before export, one-time email-action handling in React StrictMode, fresh identity for MFA changes, and configuration preflight safeguards.

Managed Google/Firebase sign-in, verified email/password, reset links, optional authenticator MFA, revocable SQL sessions, cloud preferences/drafts and one-time legacy-workspace attachment are implemented. Details and the exact owner setup are in AUTHENTICATION.md. The sibling bindr-app checkout is untouched.

## Validation

- Full backend/AI suite: 169 passed (plus 3 subtests), six existing deprecation warnings.
- Frontend: 69 checks passed, including component lifecycle tests; connected production build passed.
- Preserved integration regressions: 28 passed in the final resumed run.
- Python pip check and deployment/start shell syntax passed.
- Earlier desktop/mobile screenshots in storage/account-ui show the initial design, which the user rejected. They do not represent the current account screens. Local preview uses fake Firebase identifiers; it does not verify live Google login.

## Account screen design revision

The user requested a UI correction only. Account screens now reuse Bindr's consumer header, Brand, Button and PromiseConversation components, Nunito display headings and shared colors. The oversized split background and generic record illustration were replaced by a white layout, the existing promise conversation and a compact form card. Narrow screens show the form on its own. Authentication handlers and provider/session behavior are unchanged. The connected TypeScript/Vite build and all 69 frontend checks passed after this revision.

Preview: http://127.0.0.1:8026/login (local combined app, mock AI and placeholder Firebase identifiers). Real-provider acceptance remains pending. The user explicitly asked to work from the code; do not require app or screenshot inspection before making these UI fixes.

## Cloud setup and deployment — resumed 15 November 2026

The existing project is `project-0021b03b-28bd-43e6-9d4` (number `404714938412`); its web app is `1:404714938412:web:843284bb7eeabcb138b189`. Tushar now has Owner access. His Chrome Firebase session and Cloud Shell have both been used successfully. A fresh `~/Bindr-login-release` checkout in his Cloud Shell is on `codex/account-auth` at `888722d`.

The user explicitly chose **6–128 characters**. Registration, password reset, field limits, error/help text and setup match that range. Live read-only preflight confirmed enabled Email/Password and Google, enforced 6–128 policy, optional TOTP, improved email privacy, both Cloud Run authorized domains, the existing custom runtime role and its service-account binding. No project permissions were changed during this resumed preflight. Public Firebase configuration was saved in the Cloud Shell checkout, and the existing AI model/base URL and secret references were checked and preserved.

Password-policy revision validation: 12 setup tests and all 81 frontend checks passed, including registration/reset boundary cases and provider-policy rejection. The connected TypeScript/Vite build passed. These checks stub the external provider and do not establish live-provider success.

The Firebase console still reports **"Email template updates are currently unavailable for this project"**, including when Tushar tried to save only sender/subject branding as an Owner. No template update succeeded. Verification currently uses the default Firebase `firebaseapp.com/__/auth/action` handler. Keep that fallback; actual email delivery/reset acceptance remains pending. Do not repeat IAM Owner setup as a proposed fix for the template restriction.

A fresh Cloud SQL backup completed successfully before deployment. Cloud Build `3e1e8452-d424-4a72-9786-c22ccb0e42b5` in `asia-south1` succeeded. The existing service now serves ready revision **`bindr-00003-cm9`**, image `888722d14563-20261114230005`. The deployment preserved the existing AI model/base URL, secret references, Cloud SQL database and private evidence bucket. Never request private keys or account passwords.

Both `https://bindr-tor2633xpq-el.a.run.app` and `https://bindr-404714938412.asia-south1.run.app` passed live checks for healthy `/health`, complete Firebase `/api/v1/auth/config` with the expected web app ID, HTTP 200 `/login` and `Referrer-Policy: no-referrer`. Anonymous requests to `/api/v1/auth/me`, `/api/v1/auth/session`, `/api/v1/cases`, `/api/v1/auth/preferences` and `/api/v1/auth/drafts` returned 401. Legacy anonymous session creation returned 401. A login attempt without CSRF returned 403. Chrome rendered the actual account form with enabled Google/email controls.

The automated Google button click produced `auth/popup-blocked`. The user then clicked Google personally and reported successful sign-in. Chrome independently confirmed the signed-in `/app` workspace and Settings showing his verified Google identity. A full reload preserved his authenticated session. An activity preference was changed and saved, survived a full reload, and was then restored to its original value with a confirmed cloud save. No test cases or evidence were created. Local screenshots are saved at `storage/account-ui/live-login-2026-11-15.jpg` and `storage/account-ui/live-account-settings-2026-11-15.jpg` (ignored by Git).

Live email/password registration, verification email delivery, password reset, authenticator enrollment/challenge, two-account isolation and authenticated cross-device case/draft acceptance remain pending. Optional 2FA is currently not enabled on the user's account. The Settings screen correctly requests fresh Google authentication before enrollment after a reload. Do not claim these remaining flows have been tested.

## Next actions

The next user step is to sign out and register using a reachable email address, verify the delivered email and sign in. Then check password reset, optional TOTP and authenticated cross-device acceptance. PR #4 was checked: still open, draft and mergeable, with head `888722d1456380d4c5a370d15f49b7b9ee0d0c16`. Do not merge before required live acceptance. The user prefers quick progress and grouped commands, and has authorized using his Chrome session. Do not repeat the deployment or project setup unless a new issue requires it.

## Product expansion handoff

Latest planning revision: the supplied Part 1 report was copied verbatim to `AI_QA_REPORT_SOURCE.md` and combined with `EXTREME_TEST_REPORT.md` for issue routing (original verdicts preserved). Roadmap now has **three delivery phases**, repair first, and two balanced independently developable tracks: Akshit platform/data/API/services, Tushar AI/document engine plus frontend/capture. Read `TWO_PERSON_DELIVERY_PLAN.md`, `PARALLEL_IMPLEMENTATION_CONTRACT.md` and the owner-specific `NEW_CHAT_AKSHIT_PROMPT.md` / `NEW_CHAT_TUSHAR_PROMPT.md`. The generic prompt now routes to these. Remote account head/PR state were rechecked and unchanged. These are local planning edits, not new repairs, branches, PRs or deployments. No independent-development claim removes the final real integration gate. Older two-phase/single-worker instructions below are superseded by this revision.

The user subsequently requested a detailed implementation plan and a copyable prompt for a fresh chat, covering the full supplied product proposal. Planning artifacts are `PRODUCT_IMPLEMENTATION_PLAN.md` (two main phases with explicit work packages and acceptance checks), `PRODUCT_EXPANSION_SOURCE.md` (the source proposal, preserved verbatim) and `NEW_CHAT_IMPLEMENTATION_PROMPT.md`. The next chat should audit the repo/history and preserve this account release before executing that roadmap. This planning request did not authorize starting feature implementation in the old chat; no product code or additional deployment was changed while preparing the artifacts. The remaining account checks above still apply.
