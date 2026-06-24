# Deployment Guide

Step-by-step. Assumes:
- GCP project `exiti-agent-acreditta` exists (it does)
- You have Slack workspace admin on Acreditta (you do)
- You have `gcloud` CLI installed and authenticated locally
- You have Docker installed locally (only needed if building images locally; Cloud Build does it otherwise)

Run order:

```
1. Provision GCP
2. Drop in real secrets
3. Install Slack apps
4. Build & deploy Monitor
5. Run migrations
6. Smoke test
```

Expected time first pass: ~45 minutes.

---

## 1. Provision GCP

```bash
gcloud auth login
gcloud config set project exiti-agent-acreditta
./scripts/provision.sh
```

This is idempotent. It enables APIs, creates Cloud SQL (`db-f1-micro`), creates Secret Manager entries with `PLACEHOLDER` values, creates an Artifact Registry repo, and creates the `exit-agent-runner` service account with minimal perms.

Verify with:

```bash
gcloud sql instances list
gcloud secrets list
gcloud artifacts repositories list
```

---

## 2. Drop in real secrets

The provisioner created placeholders. Replace them with real values:

```bash
# SerpAPI
printf "YOUR_SERPAPI_KEY" | gcloud secrets versions add serpapi-key --data-file=-

# Parallel.ai
printf "YOUR_PARALLEL_KEY" | gcloud secrets versions add parallel-api-key --data-file=-

# Anthropic
printf "sk-ant-..." | gcloud secrets versions add anthropic-api-key --data-file=-

# Slack channel ID (the shared channel for all 3 agents)
printf "C0123456789" | gcloud secrets versions add slack-monitor-channel --data-file=-

# Slack bot token for Monitor (you'll get this in step 3)
printf "xoxb-..." | gcloud secrets versions add slack-monitor-token --data-file=-
```

`slack-engagement-token` and `slack-advisor-token` get filled in Phases 2/3.

---

## 3. Install Slack apps

Go to https://api.slack.com/apps → **Create New App** → **From a manifest** → select `Acreditta` workspace.

Repeat three times, pasting each manifest from `slack-manifests/`:

| Manifest | Bot name | Needed for | When to install |
|---|---|---|---|
| `monitor.json` | Acreditta Monitor | Phase 1 | **Now** |
| `engagement.json` | Acreditta Engagement | Phase 3 | Later (it has `REPLACE_ME` URLs you'll patch then) |
| `advisor.json` | Acreditta Advisor | Phase 2 | Later (same — patches after Advisor is deployed) |

After installing **Monitor**:

1. **OAuth & Permissions** → **Install to Workspace** → approve
2. Copy the **Bot User OAuth Token** (starts `xoxb-`)
3. Save it to Secret Manager: `printf "xoxb-..." | gcloud secrets versions add slack-monitor-token --data-file=-`
4. Invite the bot into the shared channel: in Slack, `/invite @Acreditta Monitor`
5. Grab the channel ID (right-click channel → Copy link → ID is the trailing `C...`); save to `slack-monitor-channel` secret

You can install Engagement and Advisor now or later — Phase 1 only needs Monitor running.

---

## 4. Build & deploy Monitor

```bash
./scripts/deploy-monitor.sh
```

This:
- Submits a Cloud Build that bakes `monitor/` + `shared/` into a container image
- Pushes to Artifact Registry
- Creates or updates the `monitor-daily` Cloud Run Job
- Wires Cloud SQL connection + injects all 6 secrets as env vars
- Creates or updates Cloud Scheduler entry at `0 13 * * *` UTC (08:00 Bogotá)

---

## 5. Run migrations

The Cloud Run Job runs Alembic on startup by default (see `monitor/entrypoint.sh`). To run them manually first time:

```bash
gcloud run jobs execute monitor-migrate --region=us-central1 --wait
```

If `monitor-migrate` job doesn't exist yet, `deploy-monitor.sh` creates it. To run migrations from your local machine instead:

```bash
# Start Cloud SQL Proxy in another terminal
cloud-sql-proxy exiti-agent-acreditta:us-central1:acreditta-exit-db --port 5433 &

# Run migrations against the proxy
export DATABASE_URL="postgresql+psycopg://app:$(gcloud secrets versions access latest --secret=db-password)@localhost:5433/exit_agent"
alembic upgrade head
```

---

## 6. Smoke test

```bash
gcloud run jobs execute monitor-daily --region=us-central1 --wait
```

Check the logs:

```bash
gcloud beta run jobs executions list --job=monitor-daily --region=us-central1 --limit=1
gcloud beta run jobs executions logs read EXECUTION_NAME --region=us-central1
```

Look for: `[done] N.Ns · M signals · 0 classify failures`. The shared Slack channel should have a fresh digest.

---

## Cost monitoring

```bash
gcloud billing accounts list
# Set up a budget alert in console.cloud.google.com/billing
```

Expected monthly:
- Cloud SQL (`db-f1-micro` 10GB) — $10–15
- Cloud Run + Scheduler — $0–5 (scales to zero when not running)
- Anthropic — $1–3 with current Monitor-only load
- SerpAPI / Parallel — existing budgets

Total new spend: ~$15–25/month for Phase 1.

---

## Troubleshooting

**`gcloud sql instances create` hangs:** Cloud SQL provisioning takes 5–10 minutes. Don't cancel.

**`PermissionDenied` errors:** Run `gcloud auth application-default login` to refresh credentials.

**Monitor runs but no Slack message:** Bot probably isn't invited to the channel. `/invite @Acreditta Monitor` in Slack.

**No articles found:** Check `data/seen_url_hashes` count via `psql` — if many entries, possibly all caught up; lower the `LOOKBACK_HOURS` env var temporarily or clear `articles` table.

**Migrations fail:** Most likely the Cloud SQL connection isn't reaching from your laptop. Use the Cloud SQL Proxy approach in step 5.
