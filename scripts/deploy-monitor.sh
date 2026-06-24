#!/usr/bin/env bash
# Builds the Monitor container, pushes to Artifact Registry,
# deploys as a Cloud Run Job, schedules daily via Cloud Scheduler.

set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-exiti-agent-acreditta}"
REGION="${GCP_REGION:-us-central1}"
DB_INSTANCE="${DB_INSTANCE:-acreditta-exit-db}"
DB_NAME="${DB_NAME:-exit_agent}"
DB_USER="${DB_USER:-app}"
ARTIFACT_REPO="${ARTIFACT_REPO:-acreditta-exit}"
SA_EMAIL="exit-agent-runner@${PROJECT_ID}.iam.gserviceaccount.com"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/monitor:latest"
JOB_NAME="monitor-daily"
SCHEDULE_NAME="monitor-daily-schedule"
SCHEDULE_CRON="${SCHEDULE_CRON:-0 13 * * *}"  # 13:00 UTC = 08:00 Bogotá

gcloud config set project "$PROJECT_ID" >/dev/null

# ──────────────────────────────────────────────────────────────────────────
# 1. Build & push
# ──────────────────────────────────────────────────────────────────────────
echo "[1/3] building & pushing $IMAGE..."
gcloud builds submit \
  --tag="$IMAGE" \
  --file=Dockerfile.monitor \
  .

# ──────────────────────────────────────────────────────────────────────────
# 2. Deploy Cloud Run Job
# ──────────────────────────────────────────────────────────────────────────
echo "[2/3] deploying Cloud Run Job $JOB_NAME..."

SECRETS="SERPAPI_KEY=serpapi-key:latest"
SECRETS="$SECRETS,PARALLEL_API_KEY=parallel-api-key:latest"
SECRETS="$SECRETS,ANTHROPIC_API_KEY=anthropic-api-key:latest"
SECRETS="$SECRETS,SLACK_BOT_TOKEN=slack-monitor-token:latest"
SECRETS="$SECRETS,SLACK_CHANNEL_ID=slack-monitor-channel:latest"
SECRETS="$SECRETS,DB_PASSWORD=db-password:latest"

ENV_VARS="DB_INSTANCE_CONNECTION_NAME=${PROJECT_ID}:${REGION}:${DB_INSTANCE}"
ENV_VARS="$ENV_VARS,DB_NAME=${DB_NAME},DB_USER=${DB_USER}"
ENV_VARS="$ENV_VARS,CLAUDE_MODEL=claude-haiku-4-5"
ENV_VARS="$ENV_VARS,USE_PARALLEL_EXTRACT=true"
ENV_VARS="$ENV_VARS,SLACK_MODE=digest"
ENV_VARS="$ENV_VARS,SERPAPI_NUM=10"
ENV_VARS="$ENV_VARS,LOOKBACK_HOURS=24"

# `gcloud run jobs deploy` is idempotent: creates if missing, replaces if present.
gcloud run jobs deploy "$JOB_NAME" \
  --image="$IMAGE" \
  --region="$REGION" \
  --service-account="$SA_EMAIL" \
  --set-cloudsql-instances="${PROJECT_ID}:${REGION}:${DB_INSTANCE}" \
  --set-secrets="$SECRETS" \
  --set-env-vars="$ENV_VARS" \
  --task-timeout=15m \
  --max-retries=1 \
  --memory=512Mi \
  --cpu=1 \
  --quiet

# ──────────────────────────────────────────────────────────────────────────
# 3. Cloud Scheduler — daily trigger
# ──────────────────────────────────────────────────────────────────────────
echo "[3/3] scheduling $SCHEDULE_NAME ($SCHEDULE_CRON UTC)..."

JOB_URI="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run"

if gcloud scheduler jobs describe "$SCHEDULE_NAME" --location="$REGION" >/dev/null 2>&1; then
  gcloud scheduler jobs update http "$SCHEDULE_NAME" \
    --location="$REGION" \
    --schedule="$SCHEDULE_CRON" \
    --uri="$JOB_URI" \
    --http-method=POST \
    --oauth-service-account-email="$SA_EMAIL" \
    --quiet
  echo "  ✓ updated"
else
  gcloud scheduler jobs create http "$SCHEDULE_NAME" \
    --location="$REGION" \
    --schedule="$SCHEDULE_CRON" \
    --uri="$JOB_URI" \
    --http-method=POST \
    --oauth-service-account-email="$SA_EMAIL" \
    --time-zone="Etc/UTC" \
    --quiet
  echo "  ✓ created"
fi

echo ""
echo "✅ Done."
echo "   Smoke test: gcloud run jobs execute $JOB_NAME --region=$REGION --wait"
