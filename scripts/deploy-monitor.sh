#!/usr/bin/env bash
# Builds the Monitor container, pushes to Artifact Registry,
# deploys two Cloud Run Jobs (weekly en+es, biweekly pt),
# schedules via Cloud Scheduler.

set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-exiti-agent-acreditta}"
REGION="${GCP_REGION:-us-central1}"
DB_INSTANCE="${DB_INSTANCE:-acreditta-exit-db}"
DB_NAME="${DB_NAME:-exit_agent}"
DB_USER="${DB_USER:-app}"
ARTIFACT_REPO="${ARTIFACT_REPO:-acreditta-exit}"
SA_EMAIL="exit-agent-runner@${PROJECT_ID}.iam.gserviceaccount.com"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/monitor:latest"

gcloud config set project "$PROJECT_ID" >/dev/null

# ──────────────────────────────────────────────────────────────────────────
# 1. Build & push
# ──────────────────────────────────────────────────────────────────────────
echo "[1/4] building & pushing $IMAGE..."
gcloud builds submit \
  --config=cloudbuild.monitor.yaml \
  --substitutions=_IMAGE="$IMAGE" \
  .

# ──────────────────────────────────────────────────────────────────────────
# Shared config
# ──────────────────────────────────────────────────────────────────────────
SECRETS="SERPAPI_KEY=serpapi-key:latest"
SECRETS="$SECRETS,PARALLEL_API_KEY=parallel-api-key:latest"
SECRETS="$SECRETS,ANTHROPIC_API_KEY=anthropic-api-key:latest"
SECRETS="$SECRETS,SLACK_BOT_TOKEN=slack-monitor-token:latest"
SECRETS="$SECRETS,SLACK_CHANNEL_ID=slack-monitor-channel:latest"
SECRETS="$SECRETS,DB_PASSWORD=db-password:latest"

BASE_ENV="DB_INSTANCE_CONNECTION_NAME=${PROJECT_ID}:${REGION}:${DB_INSTANCE}"
BASE_ENV="$BASE_ENV,DB_NAME=${DB_NAME},DB_USER=${DB_USER}"
BASE_ENV="$BASE_ENV,CLAUDE_MODEL=claude-haiku-4-5"
BASE_ENV="$BASE_ENV,USE_PARALLEL_EXTRACT=true"
BASE_ENV="$BASE_ENV,SLACK_MODE=digest"
BASE_ENV="$BASE_ENV,SERPAPI_NUM=10"

COMMON_FLAGS=(
  --image="$IMAGE"
  --region="$REGION"
  --service-account="$SA_EMAIL"
  --set-cloudsql-instances="${PROJECT_ID}:${REGION}:${DB_INSTANCE}"
  --set-secrets="$SECRETS"
  --task-timeout=30m
  --max-retries=1
  --memory=512Mi
  --cpu=1
  --quiet
)

# ──────────────────────────────────────────────────────────────────────────
# 2. Weekly job (en + es) — no --lang override needed, uses config default
# ──────────────────────────────────────────────────────────────────────────
JOB_WEEKLY="monitor-weekly"
echo "[2/4] deploying Cloud Run Job $JOB_WEEKLY..."
gcloud run jobs deploy "$JOB_WEEKLY" \
  "${COMMON_FLAGS[@]}" \
  --set-env-vars="$BASE_ENV,LOOKBACK_HOURS=168"

# ──────────────────────────────────────────────────────────────────────────
# 3. Biweekly job (pt only) — passes --lang pt via args override
# ──────────────────────────────────────────────────────────────────────────
JOB_PT="monitor-pt-biweekly"
echo "[3/4] deploying Cloud Run Job $JOB_PT..."
gcloud run jobs deploy "$JOB_PT" \
  "${COMMON_FLAGS[@]}" \
  --set-env-vars="$BASE_ENV,LOOKBACK_HOURS=360" \
  --args="--lang,pt"

# ──────────────────────────────────────────────────────────────────────────
# 4. Cloud Scheduler
# ──────────────────────────────────────────────────────────────────────────
echo "[4/4] scheduling..."

schedule_job() {
  local SCHED_NAME="$1" CRON="$2" JOB="$3"
  local JOB_URI="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB}:run"
  if gcloud scheduler jobs describe "$SCHED_NAME" --location="$REGION" >/dev/null 2>&1; then
    gcloud scheduler jobs update http "$SCHED_NAME" \
      --location="$REGION" \
      --schedule="$CRON" \
      --uri="$JOB_URI" \
      --http-method=POST \
      --oauth-service-account-email="$SA_EMAIL" \
      --quiet
    echo "  ✓ $SCHED_NAME updated"
  else
    gcloud scheduler jobs create http "$SCHED_NAME" \
      --location="$REGION" \
      --schedule="$CRON" \
      --uri="$JOB_URI" \
      --http-method=POST \
      --oauth-service-account-email="$SA_EMAIL" \
      --time-zone="Etc/UTC" \
      --quiet
    echo "  ✓ $SCHED_NAME created"
  fi
}

# Weekly: every Monday 13:00 UTC = 08:00 Bogotá
schedule_job "monitor-weekly-schedule" "0 13 * * 1" "$JOB_WEEKLY"

# Biweekly pt: 1st and 15th of each month, 13:00 UTC
schedule_job "monitor-pt-biweekly-schedule" "0 13 1,15 * *" "$JOB_PT"

# Clean up old daily schedule if it exists
if gcloud scheduler jobs describe "monitor-daily-schedule" --location="$REGION" >/dev/null 2>&1; then
  gcloud scheduler jobs delete "monitor-daily-schedule" --location="$REGION" --quiet
  echo "  ✓ removed old daily schedule"
fi

echo ""
echo "✅ Done."
echo "   Weekly smoke:    gcloud run jobs execute $JOB_WEEKLY --region=$REGION --wait"
echo "   PT smoke:        gcloud run jobs execute $JOB_PT --region=$REGION --wait"
