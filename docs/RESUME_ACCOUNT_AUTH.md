# Account authentication handoff — 15 November 2026

## Current branch and implementation

Repository: bindr-google-cloud. Branch: codex/account-auth, originally based on main 893b804. Initial save was 0f79fb9. The resumed review fixed cross-tab account/session races, automatic restoration of saved cloud wording, stale facts before export, one-time email-action handling in React StrictMode, fresh identity for MFA changes, and configuration preflight safeguards.

Managed Google/Firebase sign-in, verified email/password, reset links, optional authenticator MFA, revocable SQL sessions, cloud preferences/drafts and one-time legacy-workspace attachment are implemented. Details and the exact owner setup are in AUTHENTICATION.md. The sibling bindr-app checkout is untouched.

## Validation

- Full backend/AI suite: 169 passed (plus 3 subtests), six existing deprecation warnings.
- Frontend: 69 checks passed, including component lifecycle tests; connected production build passed.
- Preserved integration regressions: 28 passed in the final resumed run.
- Python pip check and deployment/start shell syntax passed.
- Earlier desktop/mobile screenshots: storage/account-ui/login-desktop.jpg and register-mobile.jpg. Local preview used fake Firebase identifiers; it did not verify live Google login.

## Owner gate

Akshit owns project project-0021b03b-28bd-43e6-9d4. Tushar does not have access. Akshit must add Firebase/Identity Platform to that same project, enable Google and Email/Password, enforce the password policy, run the setup script and deploy. Do not request private keys or his password. Do not claim the account system is live until real-provider acceptance in AUTHENTICATION.md is complete.

The old live anonymous MVP has not been changed. No cloud resources have been changed in this chat. Deployment of this branch refuses incomplete identity settings and rejects anonymous production mode. Keep existing AUTH_SECRET, database and evidence bucket to preserve old records.

## Next actions

Inspect remote PR status for codex/account-auth and current CI before further Git actions. Complete any CI fixes, then hand the owner the setup guide. Actual OAuth consent/email/TOTP/cross-device acceptance remains pending on his project. No account feature should be merged/deployed without checking these prerequisites.
