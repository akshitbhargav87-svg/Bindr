# Existing Google Cloud service: connected v2 update

The owner supplied current Cloud Shell output on 15 November 2026: existing `bindr` service, revision `bindr-00003-cm9`, explicit `bindr-runtime` identity, same-project Mumbai Cloud SQL attachment, GCS evidence backend, Firebase configuration, real Meta provider selection and signing/database/model Secret Manager references. Configuration presence is not live-provider acceptance.

`scripts/release_existing_google_cloud.py` is a real rollout utility for this existing setup. Run from an independent clean checkout in owner-authenticated Cloud Shell:

```bash
python3 scripts/release_existing_google_cloud.py project-0021b03b-28bd-43e6-9d4 --region asia-south1
```

It builds the connected image under the existing builder identity, captures its digest, creates and confirms a fresh SQL backup, executes the additive schema-11 migration in a single-task/no-retry Cloud Run Job, creates a maintenance-only worker, and schedules authenticated minute invocation. The dedicated scheduler identity receives `roles/run.invoker` only on the maintenance job. Export generation/expiry and requested case/account deletion are included; external correspondence, reply polling and reminders are excluded by the worker's job-kind filter. Notification/FCM/Gmail-send flags are set false in the worker and new web revision.

The web update changes the image and those explicit optional-feature flags while retaining existing environment, secret references, storage, service identity and IAM. It starts without moving traffic, checks revision readiness and retained environment, then explicitly cuts over. Cloud Run startup readiness and migration completion are deployment operations, not full application acceptance. A source/image/backup/revision record is stored under ignored `storage/release-*.json`. A traffic rollback command is printed; it does not reverse database changes. Backup restoration has not been rehearsed by this utility.

The utility creates billable Cloud Build/Run Job/Scheduler/backup work using existing resources; it does not recreate databases, buckets, credentials, accounts or original evidence. It stops on cloud command failure. Send the failed numbered stage/error instead of rerunning initial resource or secret generation. A failed later stage may leave the confirmed additive schema update and configured maintenance resources in place; no destructive rollback is attempted.

Per the owner's request, no local tests, build, live provider call or cloud execution was run after these edits. Earlier acceptance counts are preserved and do not validate this utility or its new maintenance-only filter. Real Meta, real browser and controlled account/privacy acceptance remain unverified; this utility does not issue product sign-off.

Command references: [Cloud Build submit](https://docs.cloud.google.com/sdk/gcloud/reference/builds/submit), [SQL backup](https://docs.cloud.google.com/sdk/gcloud/reference/sql/backups/create), [Cloud Run job deploy](https://docs.cloud.google.com/sdk/gcloud/reference/run/jobs/deploy), [authenticated job scheduling](https://docs.cloud.google.com/run/docs/execute/jobs-on-schedule), [no-traffic service deployment](https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy).

## First owner-run rollout observation

The owner supplied Cloud Shell screenshots showing source `6eaebc69b97d` built successfully, the updater advancing through backup/migration/worker scheduling, scheduler `bindr-maintenance-minute` enabled, and revision `bindr-v2-6eaebc69-022612` deployed at 0% traffic. The original utility then stopped at its aggregate service `latestReadyRevisionName` equality check. Traffic cutover and live application acceptance are not established by those screenshots. The utility now checks the immutable revision's observed generation/Ready condition, image digest and retained environment instead. This source-only utility fix does not require rebuilding the already-deployed application image. Resume the existing revision's readiness check/cutover rather than rerunning the full build/migration. No local tests were rerun.
