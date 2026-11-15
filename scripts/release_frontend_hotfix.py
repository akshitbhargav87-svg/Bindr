"""Build only frontend assets over an existing v2 backend image and cut over.

Run in owner-authenticated Cloud Shell. No schema migration, backup or worker
replacement. Existing runtime settings, secret references and service IAM remain.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project")
    parser.add_argument("--region", default="asia-south1")
    parser.add_argument("--base-revision", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", args.project):
        parser.error("Use a Google Cloud project ID")
    if not re.fullmatch(r"[a-z]+-[a-z]+[0-9]+", args.region):
        parser.error("Use a Google Cloud region")
    if not re.fullmatch(r"bindr-[a-z0-9-]+", args.base_revision):
        parser.error("Use the existing v2 revision name")
    os.chdir(Path(__file__).resolve().parents[1])
    if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
        raise SystemExit("Use a clean independent checkout")
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    common = [f"--project={args.project}", "--quiet"]
    run_common = [*common, f"--region={args.region}"]

    def gcloud(*parts, output=False, regional=False):
        result = subprocess.run(["gcloud", *parts, *(run_common if regional else common),
                                 *(["--format=json"] if output else [])],
                                check=True, text=True, stdout=subprocess.PIPE if output else None)
        return json.loads(result.stdout) if output else None

    def service():
        return gcloud("run", "services", "describe", "bindr", output=True, regional=True)

    print("1/3 Reading deployed v2 base image and preserving runtime configuration", flush=True)
    initial = service()
    base = gcloud("run", "revisions", "describe", args.base_revision, output=True, regional=True)
    if not any(c.get("type") == "Ready" and c.get("status") == "True"
               for c in base.get("status", {}).get("conditions", [])):
        raise SystemExit("The requested v2 base revision is not ready")
    image_base = base.get("status", {}).get("imageDigest", "")
    if not re.fullmatch(re.escape(f"{args.region}-docker.pkg.dev/{args.project}/")
                        + r"[^\s@]+@sha256:[a-f0-9]{64}", image_base):
        raise SystemExit("Expected an existing same-project immutable Artifact Registry image")
    traffic = [t for t in initial.get("status", {}).get("traffic", []) if t.get("percent", 0)]
    if len(traffic) != 1 or traffic[0].get("percent") != 100:
        raise SystemExit("Review the current traffic split before applying this hotfix")
    old_revision = traffic[0]["revisionName"]
    original_created = initial.get("status", {}).get("latestCreatedRevisionName")
    original_template = initial["spec"]["template"]["spec"]
    if len(original_template["containers"]) != 1:
        raise SystemExit("Expected the existing single-container service")
    image_tag = f"{args.region}-docker.pkg.dev/{args.project}/bindr/app:ui-{source[:12]}-{stamp}"
    state_path = Path("storage") / f"frontend-hotfix-{stamp}.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state = {"source": source, "old_revision": old_revision, "base_revision": args.base_revision,
             "base_image": image_base, "status": "building"}

    def save(status):
        state["status"] = status
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    save("building")
    print("2/3 Building frontend assets; reusing the existing backend and OCR image", flush=True)
    with tempfile.TemporaryDirectory(prefix="bindr-ui-build-") as temp:
        config = Path(temp) / "build.json"
        config.write_text(json.dumps({
            "steps": [{"name": "gcr.io/cloud-builders/docker", "args": [
                "build", "-f", "Dockerfile.frontend-hotfix", "--build-arg",
                f"BINDR_BASE_IMAGE={image_base}", "-t", image_tag, "."]}],
            "images": [image_tag], "options": {"logging": "CLOUD_LOGGING_ONLY"},
            "timeout": "1200s"
        }), encoding="utf-8")
        build = gcloud("builds", "submit", ".", f"--region={args.region}",
            f"--config={config}", "--suppress-logs",
            f"--service-account=projects/{args.project}/serviceAccounts/bindr-builder@{args.project}.iam.gserviceaccount.com",
            f"--gcs-source-staging-dir=gs://{args.project}-bindr-builds/source", output=True)
    digest = next((i.get("digest") for i in build.get("results", {}).get("images", [])
                   if i.get("name") == image_tag), "")
    if build.get("status") != "SUCCESS" or not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise SystemExit("Hotfix build did not return a successful immutable image")
    image = image_tag.rsplit(":", 1)[0] + "@" + digest
    state["image"] = image
    state["build_id"] = build.get("id")
    save("built")
    before = service()
    if (before.get("status", {}).get("latestCreatedRevisionName") != original_created
            or before["spec"]["template"]["spec"] != original_template
            or [t for t in before.get("status", {}).get("traffic", []) if t.get("percent", 0)] != traffic):
        raise SystemExit("Deployment changed during the build; hotfix not applied")
    suffix = f"ui-{source[:8]}-{stamp[-6:]}"
    revision_name = "bindr-" + suffix
    state["new_revision"] = revision_name
    save("starting_revision")
    print("3/3 Starting the hotfix without traffic, then switching after readiness", flush=True)
    gcloud("run", "deploy", "bindr", f"--image={image}", f"--revision-suffix={suffix}",
           "--no-traffic", "--deploy-health-check", regional=True)
    revision = None
    for attempt in range(12):
        revision = gcloud("run", "revisions", "describe", revision_name, output=True, regional=True)
        ready = next((c for c in revision.get("status", {}).get("conditions", [])
                      if c.get("type") == "Ready"), {})
        if ready.get("status") == "True":
            break
        if ready.get("status") == "False" or attempt == 11:
            raise SystemExit("Hotfix revision is not ready; live traffic unchanged")
        time.sleep(5)
    def environment(spec):
        return {e["name"]: e for e in spec["containers"][0].get("env", [])}
    if (environment(revision["spec"]) != environment(original_template)
            or revision["spec"].get("serviceAccountName") != original_template.get("serviceAccountName")
            or revision.get("status", {}).get("imageDigest") != image):
        raise SystemExit("Unexpected runtime/image change; live traffic unchanged")
    final = service()
    if final.get("status", {}).get("latestCreatedRevisionName") != revision_name:
        raise SystemExit("Another deployment appeared; live traffic unchanged")
    sql = "run.googleapis.com/cloudsql-instances"
    if revision.get("metadata", {}).get("annotations", {}).get(sql) != initial["spec"]["template"].get("metadata", {}).get("annotations", {}).get(sql):
        raise SystemExit("Cloud SQL configuration changed; live traffic unchanged")
    save("ready_without_traffic")
    gcloud("run", "services", "update-traffic", "bindr", f"--to-revisions={revision_name}=100", regional=True)
    save("deployed")
    print("DEPLOYED:", final.get("status", {}).get("url"), flush=True)
    print("REVISION:", revision_name, flush=True)
    print("Frontend hotfix only; no migration, worker update or model request was performed.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError:
        raise SystemExit("Cloud command failed. Send the error above. Do not rerun database setup.") from None
