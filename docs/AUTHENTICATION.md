# Account authentication: implementation and owner setup

This change adds Google sign-in, email/password registration, verified-email access, password-reset links and optional authenticator-app two-factor authentication. The UI uses Bindr's existing typefaces, colours and components. Project setup has been verified by an owner; **live-provider acceptance remains required**. See RESUME_ACCOUNT_AUTH.md for the current deployment status. Do not describe the full account launch as complete until the acceptance sequence below passes.

For a forwardable checklist with checkout commands, deployment and the exact results to return, use [Login launch checklist](LOGIN_LAUNCH_CHECKLIST.md).

## Where data lives

Google Firebase Authentication with Identity Platform holds login identities, password hashes and enrolled MFA secrets. Bindr does not store passwords, Google refresh tokens or TOTP secrets. Cloud SQL holds stable account IDs, hashed random session tokens, case ownership, saved complaint wording and activity preferences/read markers. Existing cases and evidence metadata stay in the same database; immutable originals stay in the existing private GCS bucket. No Firestore database or new public evidence bucket is needed.

Browser authentication tokens use in-memory Firebase persistence. Bindr exchanges a freshly authenticated, verified Firebase ID token for a random HttpOnly, Secure, SameSite=Lax cookie valid for five days by default. The browser stores the access cookie, not case files or password credentials. Unsaved form edits necessarily remain in memory; choose Save draft to persist complaint wording. The separate offline demo still uses temporary data.

Every protected request checks the database session, Google account existence/disabled state, token-revocation time and enrolled-factor fingerprint. Password resets, account disabling/deletion and factor changes end access. Signing out revokes that database session; signing out all devices also revokes Google's refresh tokens. Session creation checks the ID token signature, audience, issuer and revocation with Google's Admin SDK, requires a login within five minutes and rejects unverified email, anonymous/custom providers and first-factor-only tokens for MFA accounts. Client-side flags cannot grant access. Cookie writes require a permitted Origin, matching CSRF token and the tab’s expected account ID. Account switches in another tab invalidate stale requests; the UI rechecks identity on focus and broadcasts sign-in/sign-out changes without sending credentials.

The legacy anonymous cookie only authorizes a separately confirmed transfer of that browser's cases after account sign-in. An atomic, unique workspace claim prevents replay to another account. It cannot log in to protected APIs. Expired or lost legacy cookies cannot recover old records automatically. Keep the existing AUTH_SECRET, database and evidence bucket during migration.

## Project owner: one-time setup in the existing project

Use **project-0021b03b-28bd-43e6-9d4**, not a new project. Both Akshit and Tushar now have owner access. No account passwords or private keys need to be shared in chat.

1. Open the [Firebase console](https://console.firebase.google.com/). Add Firebase to the **existing Google Cloud project** if it is not listed. Accept any required service terms personally. The site, Cloud SQL database, evidence bucket and Meta configuration remain in place.
2. Enable **Authentication with Identity Platform** for that project. Google's managed TOTP MFA requires this upgrade. Review the displayed billing/usage terms before enabling it. See [Google's TOTP guide](https://firebase.google.com/docs/auth/web/totp-mfa).
3. Under Authentication → Sign-in method, enable **Email/Password** and **Google**. Choose the proper project support email for Google and keep one account per email. Do not enable anonymous sign-in.
4. Under Authentication → Settings → Password policy, use **Require**, minimum **6**, maximum **128** characters. Long passphrases are supported; the application also calls Google's policy validator. Enable email enumeration protection if the console offers it (the script below enables improved email privacy).
5. Register a **Web app** named Bindr in Project settings → General. Firebase Hosting and Analytics are not required. Copy its public app ID (`1:...:web:...`). Do not download a service-account private key.
6. In Cloud Shell, from the updated repository root, run:

   ```bash
   export PROJECT_ID="project-0021b03b-28bd-43e6-9d4"
   export REGION="asia-south1"
   gcloud config set project "$PROJECT_ID"
   gcloud services enable identitytoolkit.googleapis.com firebase.googleapis.com
   python3 scripts/configure_google_auth.py "$PROJECT_ID" "YOUR_FIREBASE_WEB_APP_ID" --region "$REGION"
   ```

   The script checks email/password and Google are enabled, anonymous access is disabled and the 6–128-character password policy is enforced before making changes. It enables optional TOTP with at most one adjacent interval, preserves stricter MFA settings and other factor providers, adds both current Cloud Run hostnames as authorized domains, enables email privacy and grants the runtime service account only `firebaseauth.users.get` and `firebaseauth.users.update`. The update permission is required for global session revocation. It saves public web configuration to ignored `deploy/account-auth.env`. There are no new server credentials.
7. Under Authentication → Templates, set the verification and password-reset sender/app name to Bindr and the **custom action URL** to `https://bindr-404714938412.asia-south1.run.app/auth/action`. If Google's console does not accept this custom handler, retain the default Firebase handler: email verification/reset still works, and the continue link returns to Bindr. Verify actual email delivery and branding before claiming it is configured.
   Application access logs are disabled to avoid logging one-time email-action codes. If you choose the custom handler, configure Cloud Logging retention/exclusions for Cloud Run request URLs containing `/auth/action?`; ingress request logging is separate from application logging. Bindr uses `Referrer-Policy: no-referrer`.
8. Check Authentication → Settings → Authorized domains includes the exact hostname used for judging and the alternate service URL printed by Cloud Run. Keep the Firebase-generated API restrictions on the Firebase browser key, including the APIs needed for Authentication; do not allow unrelated paid Google APIs on this key. This build sends `Referrer-Policy: no-referrer`, so adding HTTP-referrer website restrictions can block its authentication requests. Do not add that restriction without a compatible referrer-policy change and real-browser validation. The web key is a public project identifier, not a server secret. See [Firebase API key guidance](https://firebase.google.com/docs/projects/api-keys) and [website restrictions](https://cloud.google.com/docs/authentication/api-keys#adding_http_restrictions).
9. Deploy the updated branch/release after reviewing the change:

   ```bash
   bash scripts/deploy-google-cloud.sh "$PROJECT_ID" "$REGION"
   ```

   The script reads `deploy/account-auth.env`, requires complete configuration before building and supplies it at runtime. New account tables are additive; existing case/file records are retained. Anonymous production authentication is rejected at startup. Local development retains explicit anonymous mode for the existing fixtures; it is not allowed in a deployed environment.

## Live acceptance required before release completion

Use two synthetic accounts and non-sensitive evidence. Do not publish passwords, cookies, verification links, reset codes or authenticator setup keys.

- Register with email/password. Confirm that an unverified address cannot open cases; verify the delivered email and sign in.
- Sign out, sign in with Google, and confirm the correct account identity. If Google and password use the same address, use the original sign-in method and Settings → Connect Google to link deliberately; never merge accounts based only on a client-supplied email.
- Create a case, upload evidence, approve extraction, save a complaint draft and change preferences. Sign in to that same account on another browser/device and verify the saved case, private original, saved draft and preferences.
- Use another account: the first account's case and original endpoints must return 404. Neither account should see the other's drafts or preferences.
- In Settings, verify identity again if requested, add an authenticator, scan its locally generated QR, enter a current code and finish enrollment. Sign in again: wrong/missing codes must fail; a valid code must work. Test Google and password first factors as applicable. Add a backup authenticator before relying on MFA.
- Remove an authenticator after reauthentication and sign in again. Google may expire the client token after unenrollment; the application ends the Bindr session and requires a new login.
- Request a password reset, follow the actual delivered link, set the new password and confirm earlier device sessions stop working. Resetting a password must not remove MFA.
- Test ordinary logout and sign out all devices. Replaying a prior cookie must fail. Global logout requires recent authentication.
- If this browser has a valid old anonymous cookie, use Settings → Attach this browser's records. Confirm preserved originals/history and that the same old cookie cannot transfer them to a second account.
- Repeat the existing evidence → extraction → review → revision → complaint → resolution lifecycle and check a saved case/file after a redeploy.

## Recovery and operational limits

Optional MFA is managed by Google. There are no application-generated backup codes or automatic MFA removal by email. Users can enroll backup authenticators; recovery after losing all factors requires an owner-operated identity-verification process. Do not remove a factor simply because someone knows an email address. Password reset intentionally does not bypass MFA. Establish a support contact and recovery policy before a public launch.

The application rate-limits session exchanges; Google enforces credential/verification throttling and the configured password policy. The current in-process limiter is a modest demo control, not a distributed abuse-prevention service. Account session rows expire logically; add scheduled retention/cleanup and audit retention policies before a larger launch. Maintain database backups, monitor authentication failures without logging credentials, and review IAM/billing settings with the project owner.

## Validation evidence

See `backend/app/tests/test_accounts.py` for real FastAPI/SQL tests with only the external identity-provider boundary stubbed. These cover verified-email/recent-login enforcement, server-side MFA, private cross-account cases/files, origin/CSRF, local/global revocation, provider failure, security changes, expiry, one-time legacy attachment and versioned cloud preferences/drafts. They are not proof that Google OAuth consent, email delivery or real TOTP enrollment has been enabled in Akshit's project. Record the live results separately when the owner completes setup.


## Reviewed implementation — 15 November 2026

Local validation after the resumed review: **169 backend/AI tests**, **69 frontend checks** (including React lifecycle/async race checks), and the connected TypeScript/Vite production build passed. The existing 28 integration regressions are also checked separately. Python dependency compatibility and shell syntax passed. The new native tests include setup safeguards and stale-tab account isolation.

Saved draft hydration now restores the saved wording automatically, preserves newer unsaved edits, and requires review of changed case facts before export. Email-verification links are consumed once even with React StrictMode effects. MFA management checks recent identity before showing a setup secret or changing factors. Google production configuration, actual emails and real TOTP enrollment remain owner-side acceptance gates.
