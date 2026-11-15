"""Update an existing configured Bindr service from owner-authenticated Cloud Shell.

Performs a real rollout, not a test: build -> backup -> additive migration ->
maintenance worker/schedule -> no-traffic service deployment -> explicit cutover.
Never reads Secret Manager payloads or replaces existing service environment/IAM.
"""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import time


def command(*args, capture=False):
    result = subprocess.run(args, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project")
    parser.add_argument("--region", default="asia-south1")
    args = parser.parse_args()
    project, region = args.project, args.region
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", project):
        parser.error("Use the existing Google Cloud project ID")
    if not re.fullmatch(r"[a-z]+-[a-z]+[0-9]+", region):
        parser.error("Use a Google Cloud region")
    os.chdir(Path(__file__).resolve().parents[1])
    if command("git", "status", "--porcelain", capture=True):
        raise SystemExit("Use a clean independent checkout before releasing")
    source = command("git", "rev-parse", "HEAD", capture=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    release_id = f"{source[:12]}-{stamp}"
    common = [f"--project={project}", "--quiet"]
    run_common = [*common, f"--region={region}"]

    def gcloud(*parts, output=False):
        return command("gcloud", *parts, *common,
                       *(["--format=json"] if output else []), capture=output)

    def describe():
        return json.loads(gcloud("run", "services", "describe", "bindr",
                                 f"--region={region}", output=True))

    print("1/7 Reading existing deployment configuration (no secret payloads)", flush=True)
    service = describe()
    template = service["spec"]["template"]
    spec = template["spec"]
    annotations = template.get("metadata", {}).get("annotations", {})
    containers = spec["containers"]
    if len(containers) != 1 or spec.get("volumes"):
        raise SystemExit("This updater requires the existing single-container service without mounted volumes")
    if any(k in annotations for k in (
        "run.googleapis.com/vpc-access-connector", "run.googleapis.com/network-interfaces"
    )):
        raise SystemExit("Review private-network inheritance before using this updater")
    cloudsql = annotations.get("run.googleapis.com/cloudsql-instances", "")
    connections = cloudsql.split(",")
    if len(connections) != 1 or not connections[0].startswith(f"{project}:{region}:"):
        raise SystemExit("Expected one existing Cloud SQL connection in this project and region")
    instance = connections[0].split(":")[-1]
    runtime = spec.get("serviceAccountName", "")
    if not runtime.endswith(f"@{project}.iam.gserviceaccount.com"):
        raise SystemExit("An explicit existing runtime service account is required")
    env = deepcopy(containers[0].get("env", []))
    plain = {e["name"]: e.get("value", "") for e in env if "valueFrom" not in e}
    if plain.get("AUTH_PROVIDER") != "firebase" or plain.get("EVIDENCE_STORAGE_BACKEND") != "gcs":
        raise SystemExit("Existing service must already use Firebase and private GCS")
    if plain.get("ENVIRONMENT") != "production" or plain.get("AI_PROVIDER") != "meta":
        raise SystemExit("Existing service must already use production and the real Meta provider")
    for key in ("FIREBASE_PROJECT_ID", "FIREBASE_API_KEY", "FIREBASE_AUTH_DOMAIN",
                "FIREBASE_APP_ID", "EVIDENCE_GCS_BUCKET"):
        if not plain.get(key):
            raise SystemExit(f"Existing configuration is missing {key}")
    aliases = {}
    for metadata in (service.get("metadata", {}), template.get("metadata", {})):
        raw = metadata.get("annotations", {}).get("run.googleapis.com/secrets", "")
        for entry in raw.split(","):
            if ":" in entry:
                alias, target = entry.split(":", 1)
                aliases[alias] = target
    secrets = {}
    for entry in env:
        if "valueFrom" in entry:
            ref = entry["valueFrom"]["secretKeyRef"]
            secrets[entry["name"]] = f"{aliases.get(ref['name'], ref['name'])}:{ref['key']}"
    if not {"AUTH_SECRET", "DATABASE_URL", "MODEL_API_KEY"}.issubset(secrets):
        raise SystemExit("Existing signing/database/model credentials must be Secret Manager references")
    old_revision = service.get("status", {}).get("latestReadyRevisionName")
    traffic = [t for t in service.get("status", {}).get("traffic", []) if t.get("percent", 0)]
    if (not old_revision or len(traffic) != 1 or traffic[0].get("percent") != 100
            or traffic[0].get("revisionName") != old_revision):
        raise SystemExit("Existing service has a traffic split; review it before cutover")
    if containers[0].get("command") or containers[0].get("args"):
        raise SystemExit("Existing service overrides the image entrypoint; review it first")
    disabled = {"NOTIFICATION_DELIVERY_ENABLED": "false", "FCM_DELIVERY_ENABLED": "false",
                "GMAIL_REVIEWED_SEND_ENABLED": "false"}
    worker_plain = {**plain, **disabled}
    image = f"{region}-docker.pkg.dev/{project}/bindr/app:{release_id}"
    builder = f"bindr-builder@{project}.iam.gserviceaccount.com"
    scheduler_sa = f"bindr-scheduler@{project}.iam.gserviceaccount.com"
    state_path = Path("storage") / f"release-{release_id}.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state = {"source": source, "old_revision": old_revision, "image": image,
             "project": project, "region": region, "status": "preparing"}

    def save(status):
        state["status"] = status
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    save("configuration_validated")
    print("Release record:", state_path, flush=True)
    # Resolve setup/access failures before building or changing the database.
    gcloud("iam", "service-accounts", "describe", builder, output=True)
    gcloud("storage", "buckets", "describe", f"gs://{project}-bindr-builds", output=True)
    gcloud("services", "enable", "cloudscheduler.googleapis.com")
    identities = json.loads(gcloud("iam", "service-accounts", "list", output=True))
    if not any(sa.get("email") == scheduler_sa for sa in identities):
        gcloud("iam", "service-accounts", "create", "bindr-scheduler",
               "--display-name=Bindr maintenance scheduler")

    print("2/7 Building connected v2 image in Cloud Build", flush=True)
    build = json.loads(gcloud("builds", "submit", ".", f"--region={region}",
        "--config=cloudbuild.yaml", "--suppress-logs", f"--substitutions=_IMAGE={image}",
        f"--service-account=projects/{project}/serviceAccounts/{builder}",
        f"--gcs-source-staging-dir=gs://{project}-bindr-builds/source", output=True))
    if build.get("status") != "SUCCESS":
        raise SystemExit("Build did not report SUCCESS; deployment stopped")
    digest = next((i.get("digest") for i in build.get("results", {}).get("images", [])
                   if i.get("name") == image), None)
    if not digest or not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise SystemExit("Cloud Build did not return the expected immutable image digest")
    image = image.rsplit(":", 1)[0] + "@" + digest
    state["image"] = image
    state["build_id"] = build.get("id")
    save("image_built")

    print("3/7 Taking and confirming a fresh Cloud SQL backup", flush=True)
    description = f"bindr-v2-{release_id}"
    gcloud("sql", "backups", "create", f"--instance={instance}", f"--description={description}")
    backups = json.loads(gcloud("sql", "backups", "list", f"--instance={instance}", output=True))
    backup = next((b for b in backups if b.get("description") == description
                   and b.get("status") == "SUCCESSFUL"), None)
    if backup is None:
        raise SystemExit("Fresh backup was not confirmed successful; database update stopped")
    state["backup_id"] = backup["id"]
    state["database_instance"] = instance
    save("backup_confirmed")
    print("Backup ID:", backup["id"], flush=True)

    with tempfile.TemporaryDirectory(prefix="bindr-release-") as temporary:
        env_file = Path(temporary) / "runtime-env.json"
        env_file.write_text(json.dumps(worker_plain), encoding="utf-8")
        env_file.chmod(0o600)
        job_args = [f"--image={image}", f"--service-account={runtime}",
                    f"--set-cloudsql-instances={cloudsql}", f"--env-vars-file={env_file}",
                    "--set-secrets=" + ",".join(f"{k}={v}" for k, v in secrets.items()),
                    "--cpu=1", "--memory=2Gi", "--tasks=1", "--parallelism=1",
                    "--max-retries=0", "--command=python", *run_common]
        migration = f"bindr-migrate-{source[:12]}"
        print("4/7 Applying the additive schema migration using the built image", flush=True)
        command("gcloud", "run", "jobs", "deploy", migration, *job_args,
                "--task-timeout=900s", "--args=-m,scripts.migrate_platform,--upgrade")
        command("gcloud", "run", "jobs", "execute", migration, "--wait", *run_common)
        save("schema_updated")

        print("5/7 Configuring maintenance worker and authenticated minute schedule", flush=True)
        command("gcloud", "run", "jobs", "deploy", "bindr-maintenance", *job_args,
                "--task-timeout=240s",
                "--args=-m,scripts.platform_worker,--max-jobs,20,--maintenance-only")
        command("gcloud", "run", "jobs", "add-iam-policy-binding", "bindr-maintenance",
                f"--member=serviceAccount:{scheduler_sa}", "--role=roles/run.invoker", *run_common)
        schedule_name = "bindr-maintenance-minute"
        schedules = json.loads(gcloud("scheduler", "jobs", "list", f"--location={region}", output=True))
        existing = next((s for s in schedules if s.get("name", "").endswith("/" + schedule_name)), None)
        mode = "update" if existing else "create"
        command("gcloud", "scheduler", "jobs", mode, "http", schedule_name,
                f"--location={region}", "--schedule=* * * * *", "--time-zone=Etc/UTC",
                f"--uri=https://run.googleapis.com/v2/projects/{project}/locations/{region}/jobs/bindr-maintenance:run",
                "--http-method=POST", "--message-body={}",
                ("--update-headers=" if existing else "--headers=") + "Content-Type=application/json",
                f"--oauth-service-account-email={scheduler_sa}",
                "--max-retry-attempts=0", "--attempt-deadline=30s", *common)
        if existing and existing.get("state") == "PAUSED":
            command("gcloud", "scheduler", "jobs", "resume", schedule_name,
                    f"--location={region}", *common)
        save("maintenance_scheduled")

    # Refuse to overwrite a deployment another owner made while the build ran.
    if describe().get("status", {}).get("latestReadyRevisionName") != old_revision:
        raise SystemExit("Service changed during preparation; not replacing its newer revision")
    suffix = f"v2-{source[:8]}-{stamp[-6:]}"
    new_revision = f"bindr-{suffix}"
    state["new_revision"] = new_revision
    save("starting_revision")
    print("6/7 Starting new revision without moving live traffic", flush=True)
    command("gcloud", "run", "deploy", "bindr", f"--image={image}", "--no-traffic",
            f"--revision-suffix={suffix}", "--port=8080", "--cpu=1", "--memory=2Gi",
            "--concurrency=4", "--timeout=300", "--execution-environment=gen2",
            "--startup-probe=httpGet.path=/health,httpGet.port=8080,periodSeconds=10,timeoutSeconds=5,failureThreshold=24",
            "--update-env-vars=" + ",".join(f"{k}={v}" for k, v in disabled.items()),
            *run_common)
    # Inspect the immutable revision itself. The service's aggregate
    # latestReadyRevisionName is not a reliable gate for a no-traffic rollout.
    revision = None
    for attempt in range(12):
        revision = json.loads(gcloud("run", "revisions", "describe", new_revision,
                                     f"--region={region}", output=True))
        status = revision.get("status", {})
        ready = next((c for c in status.get("conditions", [])
                      if c.get("type") == "Ready"), {})
        observed = str(status.get("observedGeneration"))
        generation = str(revision.get("metadata", {}).get("generation"))
        reconciled = observed != "None" and observed == generation
        if reconciled and ready.get("status") == "True":
            break
        if reconciled and ready.get("status") == "False":
            raise SystemExit("Revision reports not ready; live traffic was not moved. Inspect its Cloud Run logs.")
        if attempt == 11:
            raise SystemExit("Revision readiness is still pending; live traffic was not moved. Resume cutover without rebuilding.")
        time.sleep(5)
    latest = describe()
    # Environment order may change; compare name-indexed maps instead.
    expected_env = {e["name"]: e for e in env}
    expected_env.update({k: {"name": k, "value": v} for k, v in disabled.items()})
    actual_env = {e["name"]: e for e in revision["spec"]["containers"][0].get("env", [])}
    if expected_env != actual_env:
        raise SystemExit("Runtime environment differs unexpectedly; live traffic was not moved")
    if revision.get("status", {}).get("imageDigest") != image:
        raise SystemExit("Revision image does not match the built digest; live traffic was not moved")
    if latest.get("status", {}).get("latestCreatedRevisionName") != new_revision:
        raise SystemExit("Another revision was created during deployment; live traffic was not moved")
    save("revision_ready_without_traffic")
    print("7/7 Moving live traffic to the ready v2 revision", flush=True)
    command("gcloud", "run", "services", "update-traffic", "bindr",
            f"--to-revisions={new_revision}=100", *run_common)
    save("deployed")
    print("DEPLOYED:", latest.get("status", {}).get("url"), flush=True)
    print("REVISION:", new_revision, flush=True)
    print("SOURCE:", source, flush=True)
    print("Traffic rollback command (does not reverse schema changes):", flush=True)
    print(shlex.join(["gcloud", "run", "services", "update-traffic", "bindr",
                      f"--to-revisions={old_revision}=100", *run_common]), flush=True)
    print("Real Meta, account privacy and full-app acceptance were not run by this script.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError:
        raise SystemExit("Cloud command failed. Stopped; send the error above and the last numbered stage. Do not recreate secrets or databases.") from None
