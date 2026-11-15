# Deploy Bindr on Google Cloud

> **Combined v2 update:** Use `codex/qa-integration`. Firebase/Identity Platform setup must exist before account deployment; this chat now owns the backend closeout because Akshit is unavailable. Preserve the existing database, buckets and signing secret. Before replacing the existing service, follow the schema-11 migration and managed-worker requirements in [platform operations](platform/OPERATIONS.md) and the current [combined integration status](intelligence/COMBINED_MVP_STATUS.md). The historical live acceptance below covers an earlier revision, not this combined v2 release. The Docker build now enables v2. Existing cloud Secret Manager configuration can provide the model key; absence of a local key does not establish that the deployed service lacks one.

**Cloud Run** hosts the connected frontend/API. **Cloud SQL PostgreSQL** stores records. **Private Cloud Storage** keeps original evidence. **Secret Manager** holds credentials. The existing Meta API provider stays in place; this does not switch AI to Gemini or Vertex AI.

The judging deployment is live at https://bindr-404714938412.asia-south1.run.app. See [live acceptance results](LIVE_ACCEPTANCE.md). The one-time setup below is for recreating the deployment; for the existing resources use the update instructions. No data was imported from Render or SQLite. The supplied Console screenshot identifies **My First Project**, ID `project-0021b03b-28bd-43e6-9d4`; the commands below use that project.

## 1. Select the project and billing

Open [Google Cloud Console](https://console.cloud.google.com/), select the intended project and link billing. Set a budget alert and review the [pricing calculator](https://cloud.google.com/products/calculator) before creating resources. Render credits do not transfer. Budget alerts notify you; they do not cap charges.

The demo uses Cloud Run at 1 vCPU / 2 GiB, minimum zero and maximum one instance; a single-zone PostgreSQL 16 `db-f1-micro` instance with 10-GB SSD; two private buckets; Artifact Registry; Cloud Build; and three secrets. Cloud SQL and storage remain billable when Run scales to zero. The small shared-core database has no high availability. The release audit measured OCR alone at about 529 MiB: keep 2 GiB for the app.

## 2. Create resources once

Open **Cloud Shell** from the Console toolbar. Run these blocks in the same **Bash** shell. They create billable resources: inspect the project first. Use a project Owner or equivalent administrator. `asia-south1` is Mumbai; keep all resources in the same region.

```bash
git clone https://github.com/akshitbhargav87-svg/Bindr.git
cd Bindr
export PROJECT_ID="project-0021b03b-28bd-43e6-9d4"
export REGION="asia-south1"
gcloud config set project "$PROJECT_ID"
gcloud projects describe "$PROJECT_ID" --format='table(projectId,name)'
```

The names below are for a fresh deployment. If a resource exists, inspect it and resume at the next missing step. Do not rerun initial password/secret generation for updates.

```bash
gcloud services enable run.googleapis.com sqladmin.googleapis.com storage.googleapis.com \
  artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com \
  iam.googleapis.com logging.googleapis.com

gcloud iam service-accounts create bindr-runtime --display-name="Bindr runtime"
gcloud iam service-accounts create bindr-builder --display-name="Bindr builder"
export RUNTIME_SA="bindr-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
export BUILD_SA="bindr-builder@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud artifacts repositories create bindr --repository-format=docker --location="$REGION"
gcloud storage buckets create "gs://${PROJECT_ID}-bindr-evidence" --location="$REGION" \
  --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets create "gs://${PROJECT_ID}-bindr-builds" --location="$REGION" \
  --uniform-bucket-level-access --public-access-prevention

gcloud sql instances create bindr-db --database-version=POSTGRES_16 --edition=ENTERPRISE \
  --tier=db-f1-micro --region="$REGION" --availability-type=zonal \
  --storage-size=10 --storage-type=SSD --no-storage-auto-increase \
  --backup-start-time=03:00 --retained-backups-count=3 --deletion-protection \
  --assign-ip --server-ca-mode=GOOGLE_MANAGED_INTERNAL_CA --connector-enforcement=REQUIRED
gcloud sql databases create bindr --instance=bindr-db
```

SQL provisioning can take several minutes. It has a public IP with **no authorized networks**; Run uses an authenticated Cloud SQL connection and Unix socket. Connector enforcement rejects direct connections. Do not add `0.0.0.0/0`.

Grant the runtime access to SQL and its evidence bucket; grant the separate builder access only to build sources, images and logs:

```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${RUNTIME_SA}" --role=roles/cloudsql.client --condition=None
gcloud storage buckets add-iam-policy-binding "gs://${PROJECT_ID}-bindr-evidence" \
  --member="serviceAccount:${RUNTIME_SA}" --role=roles/storage.objectUser
gcloud storage buckets add-iam-policy-binding "gs://${PROJECT_ID}-bindr-builds" \
  --member="serviceAccount:${BUILD_SA}" --role=roles/storage.objectViewer
gcloud artifacts repositories add-iam-policy-binding bindr --location="$REGION" \
  --member="serviceAccount:${BUILD_SA}" --role=roles/artifactregistry.writer
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${BUILD_SA}" --role=roles/logging.logWriter --condition=None

DEPLOYER="$(gcloud config get-value account)"
for service_account in "$RUNTIME_SA" "$BUILD_SA"; do
  gcloud iam service-accounts add-iam-policy-binding "$service_account" \
    --member="user:${DEPLOYER}" --role=roles/iam.serviceAccountUser
done
```

The deployer bindings assume Cloud Shell is signed in as a human Google account. A service-account deployer needs a `serviceAccount:` member instead. Neither application identity needs project Editor or a downloaded JSON key. Organization policies may require an administrator to permit the public judging URL.

## 3. Add secrets privately

Keep values out of chat, Git and `VITE_` variables. In the same shell, generate the database password and signing key without printing them:

```bash
export BINDR_SQL_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(36))')"
gcloud sql users create bindr --instance=bindr-db --password="$BINDR_SQL_PASSWORD"
export CONNECTION="$(gcloud sql instances describe bindr-db --format='value(connectionName)')"

python3 -c 'import secrets; print(secrets.token_urlsafe(48), end="")' | \
  gcloud secrets create bindr-auth-secret --replication-policy=automatic --data-file=-
python3 -c 'import os; from urllib.parse import quote; print("postgresql+psycopg://bindr:" + quote(os.environ["BINDR_SQL_PASSWORD"], safe="") + "@/bindr?host=/cloudsql/" + os.environ["CONNECTION"], end="")' | \
  gcloud secrets create bindr-database-url --replication-policy=automatic --data-file=-
unset BINDR_SQL_PASSWORD

read -rsp 'Existing Meta Model API key (hidden): ' BINDR_MODEL_KEY
printf '\n'
printf '%s' "$BINDR_MODEL_KEY" | \
  gcloud secrets create bindr-model-api-key --replication-policy=automatic --data-file=-
unset BINDR_MODEL_KEY

for secret in bindr-auth-secret bindr-database-url bindr-model-api-key; do
  gcloud secrets add-iam-policy-binding "$secret" \
    --member="serviceAccount:${RUNTIME_SA}" --role=roles/secretmanager.secretAccessor
done
```

Confirm the real model and endpoint in your existing provider account. The inherited defaults are `muse-spark-1.3` and `https://api.meta.ai/v1`, still unverified with live credentials. If different, export your actual `META_MODEL` and `META_BASE_URL` before deploying. Do not put credentials in the URL. Missing credentials and provider failures stay explicit; the app does not silently enable mock AI.

## 4. Build and deploy

```bash
bash scripts/deploy-google-cloud.sh "$PROJECT_ID" "$REGION"
```

The script builds Docker in Cloud Build, including the connected frontend and OCR weights, pushes to Artifact Registry and deploys Run. Use `/health` for the public database health check: Google reserves some paths ending in `z`, including `/healthz` on this deployment. See [reserved URL paths](https://docs.cloud.google.com/run/docs/known-issues#reserved-url-paths). No local Docker installation is needed. Wait for the `/health` startup probe and record the printed HTTPS URL. Git pushes do not automatically publish revisions.

Run is publicly reachable so visitors can start a browser workspace. Cases and originals still require signed cookies and ownership checks. Original bytes travel through the authorized API, without public object URLs or a local cache. SQL and GCS are the sources of record; local container files are disposable.

Secret references are pinned to **version 1**. For rotation, add a version and change the numeric reference in the script before deploying. Preserve `AUTH_SECRET` during routine updates; changing it invalidates workspace cookies. Cookies last up to 30 days, without cross-device login or recovery. A new domain does not inherit Render's cookies.

## 5. Check the actual deployment

1. Open the HTTPS homepage and `/health`; directly refresh `/app/cases`.
2. Paste a synthetic refund message, extract, inspect the exact quote, confirm the terms and reload.
3. Upload a readable PNG/JPEG and verify OCR plus the real provider. Review uncertain dates.
4. Add/confirm a revision, inspect both versions, copy a complaint and resolve the case.
5. Download the original and compare bytes/hash. In another browser profile, confirm that case and evidence URLs are inaccessible. Verify Secure/HttpOnly session cookies.
6. Keep the first browser's cookies, deploy another revision and confirm the saved case and exact original survive. This is the persistence acceptance gate.

Additional typed frontend-to-API acceptance, from Cloud Shell in the repo:

```bash
SERVICE_URL="$(gcloud run services describe bindr --region="$REGION" --format='value(status.url)')"
cd frontend
npm ci
node checks/live-api.mjs "$SERVICE_URL"
```

This creates synthetic records and invokes the configured real extractor. Local tests with an in-memory bucket do not verify Google IAM, SQL networking, Cloud Build or live AI. Record the URL and results in [the migration audit](GOOGLE_CLOUD_MIGRATION.md) only after these checks pass.

## Updates and troubleshooting

For updates, `git pull --ff-only` and rerun the deploy script after CI passes. Preserve the database, buckets and secrets. The in-process limiter resets on instance replacement; max-instance settings may be temporarily exceeded during deployment/maintenance and are not a hard cost cap. General scaling needs a shared limiter and a schema-migration strategy.

- **Startup failure:** check revision logs, Cloud SQL attachment, database URL secret, runtime `cloudsql.client` and signing-key length.
- **Upload/download failure:** check the runtime's bucket-level `storage.objectUser`, bucket name and public-access prevention. Missing originals return 404; storage outages return 503 without provider details.
- **Build denied:** check builder Artifact Registry writer, source-bucket viewer and log writer, plus deployer `iam.serviceAccounts.actAs`.
- **AI errors:** check the real provider key/model/URL. Do not use mock mode as evidence of live AI.
- **After judging:** review/stop Cloud SQL in Console if no longer needed. Scaling Run to zero does not stop database charges. Buckets, images and backups remain billable. Decide what data to keep before deleting resources.

The [previous Render guide](DEPLOYMENT_RENDER.md) and `render.yaml` remain historical alternatives. Choose one hosting target for the judging link.

Official references: [Cloud SQL connections](https://docs.cloud.google.com/sql/docs/postgres/connect-run), [private buckets](https://docs.cloud.google.com/storage/docs/public-access-prevention), [Run secrets](https://docs.cloud.google.com/run/docs/configuring/services/secrets), [build identity](https://docs.cloud.google.com/build/docs/securing-builds/configure-user-specified-service-accounts), [Run deployment flags](https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy).
