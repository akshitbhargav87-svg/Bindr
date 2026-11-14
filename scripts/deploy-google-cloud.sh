#!/usr/bin/env bash
# Build and deploy AFTER the one-time setup in docs/DEPLOYMENT.md.
# Run from the repository root in Google Cloud Shell (Bash).
set -euo pipefail
PROJECT_ID="${1:?Usage: bash scripts/deploy-google-cloud.sh PROJECT_ID [REGION]}"
REGION="${2:-asia-south1}"
if [[ ! "$PROJECT_ID" =~ ^[a-z][a-z0-9-]{4,28}[a-z0-9]$ ]] || [[ ! "$REGION" =~ ^[a-z]+-[a-z]+[0-9]+$ ]]; then
  echo 'Use a Google Cloud project ID and region, not a display name.' >&2
  exit 2
fi
command -v gcloud >/dev/null
test -f cloudbuild.yaml
test -f Dockerfile
RUNTIME_SA="bindr-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
BUILD_SA="bindr-builder@${PROJECT_ID}.iam.gserviceaccount.com"
BUCKET="${PROJECT_ID}-bindr-evidence"
BUILD_BUCKET="${PROJECT_ID}-bindr-builds"
CONNECTION="$(gcloud sql instances describe bindr-db --project="$PROJECT_ID" --format='value(connectionName)')"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/bindr/app:$(git rev-parse --short=12 HEAD)-$(date -u +%Y%m%d%H%M%S)"

# Check setup without printing secret payloads or creating replacement resources.
for secret in bindr-auth-secret bindr-database-url bindr-model-api-key; do
  gcloud secrets versions describe 1 --secret="$secret" --project="$PROJECT_ID" --format='value(state)' | grep -qx ENABLED
done
gcloud storage buckets describe "gs://${BUCKET}" --project="$PROJECT_ID" >/dev/null

gcloud builds submit . --project="$PROJECT_ID" --region="$REGION" \
  --config=cloudbuild.yaml --substitutions="_IMAGE=${IMAGE}" \
  --service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILD_SA}" \
  --gcs-source-staging-dir="gs://${BUILD_BUCKET}/source"

gcloud run deploy bindr --project="$PROJECT_ID" --region="$REGION" \
  --image="$IMAGE" --service-account="$RUNTIME_SA" \
  --execution-environment=gen2 --port=8080 --cpu=1 --memory=2Gi \
  --min=0 --max=1 --max-instances=1 --concurrency=4 --timeout=300 \
  --allow-unauthenticated --set-cloudsql-instances="$CONNECTION" \
  --startup-probe='httpGet.path=/healthz,httpGet.port=8080,periodSeconds=10,timeoutSeconds=5,failureThreshold=24' \
  --set-env-vars="ENVIRONMENT=production,EVIDENCE_STORAGE_BACKEND=gcs,EVIDENCE_GCS_BUCKET=${BUCKET},AI_PROVIDER=meta,META_MODEL=${META_MODEL:-muse-spark-1.3},META_BASE_URL=${META_BASE_URL:-https://api.meta.ai/v1},META_TIMEOUT=45,SESSION_LIFETIME_SECONDS=2592000" \
  --set-secrets='AUTH_SECRET=bindr-auth-secret:1,DATABASE_URL=bindr-database-url:1,MODEL_API_KEY=bindr-model-api-key:1'

SERVICE_URL="$(gcloud run services describe bindr --project="$PROJECT_ID" --region="$REGION" --format='value(status.url)')"
printf 'Deployment URL: %s\n' "$SERVICE_URL"
echo 'Complete the browser and redeploy acceptance checks in docs/DEPLOYMENT.md.'
