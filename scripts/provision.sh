#!/usr/bin/env bash
# Provisions all GCP resources for the Acreditta exit-agents project.
# Idempotent — safe to re-run. Existing resources are left untouched.

set -euo pipefail

# ──────────────────────────────────────────────────────────────────────────
# Configuration — change here, nowhere else
# ──────────────────────────────────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:-exiti-agent-acreditta}"
REGION="${GCP_REGION:-us-central1}"
DB_INSTANCE="${DB_INSTANCE:-acreditta-exit-db}"
DB_NAME="${DB_NAME:-exit_agent}"
DB_USER="${DB_USER:-app}"
ARTIFACT_REPO="${ARTIFACT_REPO:-acreditta-exit}"
SA_NAME="exit-agent-runner"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "──────────────────────────────────────────────"
echo " Project: $PROJECT_ID"
echo " Region:  $REGION"
echo " DB:      $DB_INSTANCE / $DB_NAME"
echo "──────────────────────────────────────────────"

gcloud config set project "$PROJECT_ID" >/dev/null

# ──────────────────────────────────────────────────────────────────────────
# 1. Enable APIs
# ──────────────────────────────────────────────────────────────────────────
echo "[1/6] enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  sql-component.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudscheduler.googleapis.com \
  cloudbuild.googleapis.com \
  iam.googleapis.com \
  --quiet

# ──────────────────────────────────────────────────────────────────────────
# 2. Cloud SQL Postgres
# ──────────────────────────────────────────────────────────────────────────
echo "[2/6] Cloud SQL Postgres..."
if gcloud sql instances describe "$DB_INSTANCE" >/dev/null 2>&1; then
  echo "  ✓ instance $DB_INSTANCE already exists"
else
  echo "  → creating $DB_INSTANCE (this takes ~5 min)..."
  gcloud sql instances create "$DB_INSTANCE" \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region="$REGION" \
    --storage-size=10GB \
    --storage-auto-increase \
    --quiet
fi

# DB password
if gcloud secrets describe db-password >/dev/null 2>&1; then
  echo "  ✓ db-password secret already exists"
  DB_PASSWORD=$(gcloud secrets versions access latest --secret=db-password)
else
  echo "  → generating DB password..."
  DB_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)
  printf "%s" "$DB_PASSWORD" | gcloud secrets create db-password --data-file=- --quiet
fi

# DB user
if gcloud sql users list --instance="$DB_INSTANCE" | grep -q "^${DB_USER}\s"; then
  echo "  ✓ user $DB_USER already exists"
else
  echo "  → creating user $DB_USER..."
  gcloud sql users create "$DB_USER" --instance="$DB_INSTANCE" --password="$DB_PASSWORD" --quiet
fi

# Database
if gcloud sql databases list --instance="$DB_INSTANCE" | grep -q "^${DB_NAME}\s"; then
  echo "  ✓ database $DB_NAME already exists"
else
  echo "  → creating database $DB_NAME..."
  gcloud sql databases create "$DB_NAME" --instance="$DB_INSTANCE" --quiet
fi

# ──────────────────────────────────────────────────────────────────────────
# 3. Secret Manager — create placeholders for things humans must fill
# ──────────────────────────────────────────────────────────────────────────
echo "[3/6] Secret Manager placeholders..."
SECRETS=(
  serpapi-key
  parallel-api-key
  anthropic-api-key
  slack-monitor-token
  slack-monitor-channel
  slack-engagement-token
  slack-advisor-token
  slack-advisor-signing-secret
)
for secret in "${SECRETS[@]}"; do
  if gcloud secrets describe "$secret" >/dev/null 2>&1; then
    echo "  ✓ $secret"
  else
    printf "PLACEHOLDER" | gcloud secrets create "$secret" --data-file=- --quiet
    echo "  → $secret  (PLACEHOLDER — fill via: gcloud secrets versions add $secret --data-file=-)"
  fi
done

# ──────────────────────────────────────────────────────────────────────────
# 4. Artifact Registry
# ──────────────────────────────────────────────────────────────────────────
echo "[4/6] Artifact Registry..."
if gcloud artifacts repositories describe "$ARTIFACT_REPO" --location="$REGION" >/dev/null 2>&1; then
  echo "  ✓ repo $ARTIFACT_REPO exists"
else
  gcloud artifacts repositories create "$ARTIFACT_REPO" \
    --repository-format=docker \
    --location="$REGION" \
    --description="Acreditta exit-agents containers" \
    --quiet
  echo "  → created $ARTIFACT_REPO"
fi

# ──────────────────────────────────────────────────────────────────────────
# 5. Service account
# ──────────────────────────────────────────────────────────────────────────
echo "[5/6] Service account..."
if gcloud iam service-accounts describe "$SA_EMAIL" >/dev/null 2>&1; then
  echo "  ✓ $SA_EMAIL exists"
else
  gcloud iam service-accounts create "$SA_NAME" \
    --display-name="Exit Agent runner" \
    --quiet
fi

for role in \
  roles/cloudsql.client \
  roles/secretmanager.secretAccessor \
  roles/run.invoker \
  roles/artifactregistry.reader; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="$role" \
    --condition=None \
    --quiet >/dev/null
done
echo "  ✓ roles bound"

# Cloud Build SA needs permission to push to Artifact Registry
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
CLOUDBUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$CLOUDBUILD_SA" \
  --role=roles/artifactregistry.writer \
  --condition=None \
  --quiet >/dev/null || true

# ──────────────────────────────────────────────────────────────────────────
# 6. Done
# ──────────────────────────────────────────────────────────────────────────
echo "[6/6] done."
echo ""
echo "Next steps:"
echo "  1. Drop real values into placeholders:"
for secret in serpapi-key parallel-api-key anthropic-api-key slack-monitor-token slack-monitor-channel; do
  echo "       printf 'VALUE' | gcloud secrets versions add $secret --data-file=-"
done
echo "  2. Install Slack Monitor app from slack-manifests/monitor.json"
echo "  3. ./scripts/deploy-monitor.sh"
