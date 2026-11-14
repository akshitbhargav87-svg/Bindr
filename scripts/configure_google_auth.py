"""Run by the project owner in Cloud Shell after the console steps in AUTHENTICATION.md.

Uses existing gcloud login, preserves other project settings, prints no access tokens.
Only standard-library modules are needed. It configures optional TOTP, authorized
domains and the runtime role, and saves PUBLIC web config for the deployment script.
"""
import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import urllib.request
import urllib.error
from copy import deepcopy


def identity_options(current, google, domains):
    """Validate security prerequisites before making any project changes."""
    sign_in = current.get("signIn", {})
    email = sign_in.get("email", {})
    if not email.get("enabled") or not email.get("passwordRequired") or not google.get("enabled"):
        raise SystemExit("Enable Email/Password (password required) and Google in Authentication > Sign-in method, then rerun.")
    if sign_in.get("allowDuplicateEmails") or sign_in.get("anonymous", {}).get("enabled"):
        raise SystemExit("Use one account per email and disable anonymous sign-in before continuing.")
    policy = current.get("passwordPolicyConfig", {})
    versions = policy.get("passwordPolicyVersions", [])
    strength = versions[0].get("customStrengthOptions", {}) if len(versions) == 1 else {}
    minimum, maximum = strength.get("minPasswordLength"), strength.get("maxPasswordLength")
    if policy.get("passwordPolicyEnforcementState") != "ENFORCE" or minimum != 6 or maximum != 128:
        raise SystemExit("Set Authentication > Settings > Password policy to Require with minimum 6 and maximum 128 characters, then rerun. "
                         f"Google reports enforcement={policy.get('passwordPolicyEnforcementState', 'unset')}, minimum={minimum}, maximum={maximum}.")
    mfa = deepcopy(current.get("mfa", {}))
    prior = next((p for p in mfa.get("providerConfigs", []) if "totpProviderConfig" in p), {})
    providers = [p for p in mfa.get("providerConfigs", []) if "totpProviderConfig" not in p]
    providers.append({"state": "MANDATORY" if prior.get("state") == "MANDATORY" else "ENABLED",
                      "totpProviderConfig": {"adjacentIntervals": min(prior.get("totpProviderConfig", {}).get("adjacentIntervals", 1), 1)}})
    mfa.update({"state": "MANDATORY" if mfa.get("state") == "MANDATORY" else "ENABLED", "providerConfigs": providers})
    return {"mfa": mfa, "authorizedDomains": sorted(set(current.get("authorizedDomains", [])) | set(domains)),
            "emailPrivacyConfig": {"enableImprovedEmailPrivacy": True}}


def gcloud(*args, allow_missing=False):
    result = subprocess.run(["gcloud", *args], capture_output=True, text=True)
    if result.returncode:
        if allow_missing and ("NOT_FOUND" in result.stderr or "not found" in result.stderr.lower()):
            return None
        raise SystemExit("A gcloud setup command failed. Check your selected project and owner permissions.\n" + result.stderr[-1000:])
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project")
    parser.add_argument("web_app_id", help="Firebase web app ID, e.g. 1:123456:web:abc")
    parser.add_argument("--region", default="asia-south1")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", args.project) or not re.fullmatch(r"[a-z]+-[a-z]+[0-9]+", args.region) or not re.fullmatch(r"[A-Za-z0-9:_-]+", args.web_app_id):
        parser.error("Use the exact project, region and Firebase web app ID.")
    token = gcloud("auth", "print-access-token", "--project=" + args.project)

    def api(url, data=None, method=None):
        request = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                         headers={"Authorization": "Bearer " + token, "Content-Type": "application/json", "X-Goog-User-Project": args.project}, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise SystemExit(f"Google setup API returned HTTP {exc.code}. Complete the Firebase/Identity Platform console setup in docs/AUTHENTICATION.md first.") from None

    base = f"https://identitytoolkit.googleapis.com/admin/v2/projects/{args.project}"
    current = api(base + "/config")
    google = api(base + "/defaultSupportedIdpConfigs/google.com")
    identity_options(current, google, [])  # Stop before any mutation if setup is incomplete.
    web = api(f"https://firebase.googleapis.com/v1beta1/projects/{args.project}/webApps/{args.web_app_id}/config")
    if web.get("projectId") != args.project or not all(web.get(k) for k in ("apiKey", "authDomain", "appId")):
        raise SystemExit("The selected Firebase web app did not return complete configuration for this project.")
    service_url = gcloud("run", "services", "describe", "bindr", "--project=" + args.project, "--region=" + args.region, "--format=value(status.url)")
    number = gcloud("projects", "describe", args.project, "--format=value(projectNumber)")
    from urllib.parse import urlparse
    host = urlparse(service_url).hostname
    if not host or not host.endswith(".run.app"):
        raise SystemExit("Could not find the existing Bindr Cloud Run hostname.")
    options = identity_options(current, google, [host, f"bindr-{number}.{args.region}.run.app"])
    api(base + "/config?updateMask=mfa,authorizedDomains,emailPrivacyConfig", options, "PATCH")
    # Only the two permissions used by token revocation/account lookup. No auth-admin role.
    role_name = "BindrIdentityRuntime"
    exists = gcloud("iam", "roles", "describe", role_name, "--project=" + args.project, "--format=value(name)", allow_missing=True)
    action = "update" if exists else "create"
    gcloud("iam", "roles", action, role_name, "--project=" + args.project, "--title=Bindr identity runtime", "--permissions=firebaseauth.users.get,firebaseauth.users.update", "--stage=GA", "--quiet")
    gcloud("projects", "add-iam-policy-binding", args.project, "--member=serviceAccount:bindr-runtime@" + args.project + ".iam.gserviceaccount.com", "--role=projects/" + args.project + "/roles/" + role_name, "--condition=None", "--quiet", "--format=none")
    public = {"FIREBASE_PROJECT_ID": args.project, "FIREBASE_API_KEY": web["apiKey"], "FIREBASE_AUTH_DOMAIN": web["authDomain"], "FIREBASE_APP_ID": web["appId"]}
    out = Path(__file__).resolve().parents[1] / "deploy" / "account-auth.env"
    out.write_text("# Public web identifiers; no passwords or server credentials.\n" + "".join(f"export {key}={shlex.quote(value)}\n" for key, value in public.items()), encoding="utf-8")
    print("Configured optional authenticator 2FA, email privacy, domains and runtime permissions.")
    print("Saved public web configuration to deploy/account-auth.env (ignored by Git).")
    print("Next: confirm the enforced 6–128-character password policy and email templates, then deploy as described in docs/AUTHENTICATION.md.")


if __name__ == "__main__":
    main()
