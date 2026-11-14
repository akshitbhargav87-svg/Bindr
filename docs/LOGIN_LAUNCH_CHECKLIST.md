# Bindr login launch: Tushar and Akshit

This updates the existing Bindr deployment. Authentication code is in draft PR #4: https://github.com/akshitbhargav87-svg/Bindr/pull/4. Automated release checks passed for the UI revision de79f28311404c326cf3052b0fa77c720fb66564. Cloud activation and real-provider tests are still required.

## Tushar: what to do now

1. Forward this checklist and PR #4 to Akshit. He owns the Google project; you do not need to install a plugin or obtain his login.
2. Agree which working email inbox will receive Bindr support/recovery requests and Google project notices. Give Akshit that address. He must select an eligible account in Google's support-email dropdown where required.
3. After he returns the deployment URL and results below, test that URL on your own computer and phone using the acceptance checklist. Send the URL and any exact error text back to this chat. Keep passwords, reset/verification links, cookies, QR codes and authenticator secrets private.

## Akshit A: enable managed authentication

Use existing project `project-0021b03b-28bd-43e6-9d4`, service `bindr`, region `asia-south1`. Preserve the existing database, evidence bucket, signing secret and Meta credentials. Do not rerun the resource-creation instructions in the original deployment guide.

1. Open https://console.firebase.google.com/ using the Google account that owns the project. Add Firebase to the existing Google Cloud project if necessary. Do not create a replacement project.
2. Open Authentication (under Security or Build in the current console). Start it if necessary, then upgrade to Authentication with Identity Platform. Review and accept the displayed usage/billing terms. The upgrade is needed for authenticator-app TOTP: https://firebase.google.com/docs/auth/web/totp-mfa.
3. In Authentication → Sign-in method, enable **Email/Password** with password sign-in enabled and **Google** with the appropriate support email. Leave anonymous sign-in disabled. Retain one account per email.
4. In Authentication → Settings → Password policy, choose **Require**, minimum **12**, maximum **128** characters, and save. The setup script refuses an unenforced or shorter minimum.
5. In Project settings → General → Your apps, register a **Web app** named Bindr. Hosting and Analytics are not needed. Copy its public **App ID**, shaped like `1:123456:web:abcdef`. This is not the project ID or API key.
6. In Google Cloud Console → Google Auth Platform, review Branding (Bindr name and working contact emails) and Audience. A public launch must allow external Google users. Complete Google's production publishing requirements shown there; report any requested brand/domain verification instead of assuming it has passed. Bindr requests basic identity scopes only, not Gmail or Drive access. See https://support.google.com/cloud/answer/15549945.

## Akshit B: get the actual login branch and configure it

Open Cloud Shell from the Google Cloud Console toolbar. Use Bash. In a fresh directory run:

```bash
git clone --branch codex/account-auth --single-branch https://github.com/akshitbhargav87-svg/Bindr.git Bindr-login-release
cd Bindr-login-release
git log -1 --oneline
export PROJECT_ID="project-0021b03b-28bd-43e6-9d4"
export REGION="asia-south1"
gcloud config set project "$PROJECT_ID"
gcloud services enable identitytoolkit.googleapis.com firebase.googleapis.com
```

If `Bindr-login-release` already exists, use another fresh directory name; do not overwrite an existing checkout. Authorize Cloud Shell with your own account if Google asks. For this revision, the commit begins `de79f28`; if the branch has advanced, confirm the intended revision with Tushar.

Replace `PASTE_FIREBASE_WEB_APP_ID_HERE` with the App ID copied in A5, then run:

```bash
python3 scripts/configure_google_auth.py "$PROJECT_ID" "PASTE_FIREBASE_WEB_APP_ID_HERE" --region "$REGION"
```

Expected: the script confirms optional authenticator 2FA, email privacy, authorized domains and runtime permissions; it creates `deploy/account-auth.env`. It uses the Cloud Run service account, so do not generate or share a service-account JSON key. If a command fails, stop and return its error text; do not continue to deploy with incomplete setup.

## Akshit C: emails, domains and the browser key

1. In Authentication → Templates, edit **Email address verification** and **Password reset**. Use Bindr as the app/sender display name and set the reply-to support address where offered.
2. Set their custom action URL to `https://bindr-404714938412.asia-south1.run.app/auth/action` so the links use Bindr's screens. Save both templates. If Google refuses that handler, report the error; the default Firebase handler is a working fallback, but report which handler was used.
3. For the custom handler, prevent its one-time codes from being retained in request logs. In Google Cloud → Logging → Logs Router → `_Default` → Edit sink → exclusion filters, add an exclusion named `bindr-auth-action-urls` with:

   ```text
   resource.type="cloud_run_revision"
   resource.labels.service_name="bindr"
   httpRequest.requestUrl:"/auth/action"
   ```

   Apply the exclusion to any additional request-log export sinks you configured. Application access logging is already disabled; Cloud Run ingress request logging is separate.
4. In Authentication → Settings → Authorized domains, confirm `bindr-404714938412.asia-south1.run.app` and the alternate Cloud Run hostname found by the setup script are listed. Add any additional actual launch hostname before using it for login.
5. In Google Cloud → APIs & Services → Credentials, retain the Firebase browser key's Firebase API restrictions. Do not add unrelated APIs. Do not add HTTP-referrer website restrictions to this build: its `no-referrer` policy can cause those requests to be rejected. Never substitute the Meta model API key here. See https://firebase.google.com/docs/projects/api-keys.

## Akshit D: preserve the current provider, back up and deploy

Before deployment, open Google Cloud → Cloud Run → `bindr` → current revision → Variables & Secrets. Read the existing non-secret `META_MODEL` and `META_BASE_URL` values. Export those exact values in the same Cloud Shell:

```bash
export META_MODEL="PASTE_EXISTING_META_MODEL_VALUE"
export META_BASE_URL="PASTE_EXISTING_META_BASE_URL_VALUE"
```

If either value is absent, resolve the correct current provider settings before continuing. The deployment script otherwise supplies defaults; do not accidentally change the existing AI provider while adding login. Keep the existing Secret Manager entries and their active version references. No secret values should be printed or pasted into chat.

Create a database backup, wait for success, then deploy in the same shell:

```bash
gcloud sql backups create --instance=bindr-db --project="$PROJECT_ID"
bash scripts/deploy-google-cloud.sh "$PROJECT_ID" "$REGION"
```

This deploys to the existing live `bindr` service and changes visitors from anonymous access to account login. It builds the branch remotely; no local Docker installation is required. Record the printed HTTPS URL and deployed commit. Open `URL/health` and `URL/login`; require a successful health response and the new sign-in screen. Verify automatic Cloud SQL backups remain enabled.

## Together E: prove that login and cloud storage work

Use two test accounts with different email addresses and non-sensitive evidence. Perform these on the actual HTTPS deployment, not the localhost preview.

| Check | Required result |
| --- | --- |
| Email registration | Registration succeeds; cases stay inaccessible until the actual received email is verified. |
| Google login | A Google account can sign in and sees the correct account identity; test an account outside the project team. |
| Password reset | The actual email arrives; its link changes the password; the old password and earlier sessions stop working. |
| Optional 2FA | Settings enrollment and a correct code succeed; after logout, wrong/missing codes fail. Enroll a backup authenticator, test it, then test removal. Password reset must not bypass 2FA. |
| Cloud persistence | On computer, create a case, upload an original, confirm extraction and save a complaint draft/preferences. On phone, sign in to the same account and see those saved items. Unsaved typing is not a saved draft. |
| Isolation | Account B cannot see account A's cases/drafts/preferences. A's case and original-file URLs must deny B access. |
| Logout | Logout ends access; Sign out all devices also ends the other device's access. |
| Existing records | If a valid old browser workspace exists, Settings → Attach this browser's records preserves its cases/history/originals; it cannot be attached to a second account. |
| Existing app flow | Evidence → extraction → review → revision → complaint → resolution still works with the real provider. |
| Redeploy | Deploy the same code again; previously saved cases, originals and drafts remain accessible to their owner. |

Return pass/fail for each row and exact error text for any failure. Do not return passwords, cookies or email action links.

## Finish and public-launch operations

After the real-provider checks pass, review PR #4, mark it ready, merge the tested change, and deploy the approved main revision. Repeat login, health and saved-record checks. A GitHub push or merge alone does not run the Cloud Run deployment script.

Before inviting public users, assign a monitored support/recovery inbox and an owner who will handle lost authenticators using an agreed identity-verification process; knowing an email address alone is not proof. Confirm database backup/restore readiness and a working health/error alert delivered to the owner. In Cloud Monitoring, create an HTTPS uptime check for the deployed `/health` URL and configure its failure alert to that inbox.

The current release remains a single-instance deployment with an in-memory abuse limiter. A distributed abuse limiter, scheduled expired-session cleanup and documented retention are remaining engineering work before a larger public launch; cloud activation alone does not implement them. Return these to Codex as engineering tasks, rather than asking Tushar to configure code he does not have.

## Akshit: send back this completion report

```text
Project: project-0021b03b-28bd-43e6-9d4
Deployed commit:
Deployment URL:
Firebase/Identity Platform enabled: yes/no
Google + Email/Password enabled: yes/no
Enforced minimum 12 characters: yes/no
Optional authenticator TOTP configured: yes/no
Email verification/reset handler: Bindr / Firebase default
External Google account login tested: pass/fail
Actual verification and reset emails tested: pass/fail
Acceptance table results:
Database backup completed and automatic backups enabled: yes/no
Health alert recipient:
Support/recovery owner and inbox:
Any errors or remaining Google approval requirements:
```
