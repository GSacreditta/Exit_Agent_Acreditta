# Acreditta Exit Agents

Three-agent system to support Acreditta's strategic exit process. Single Slack channel; shared Postgres state; one repo.

| Agent | Status | Role |
|---|---|---|
| **Monitor** (`acreditta-monitor`) | ✅ Live (Phase 1) | Daily M&A signal scanner. Posts to channel. |
| **Engagement** (`acreditta-engagement`) | 🚧 Stubbed (Phase 3) | Outreach opportunity tracker. |
| **Advisor** (`acreditta-advisor`) | 🚧 Stubbed (Phase 2) | M&A coach for Anabella. Sonnet-backed. |

**Design principle:** minimize AI, maximize plain code. Each agent uses exactly one LLM call where judgment is genuinely required — everything else is deterministic.

---

## Repo layout

```
acreditta-exit/
├── monitor/                ← Agent 1 (live)
├── engagement/             ← Agent 2 (stubbed)
├── advisor/                ← Agent 3 (stubbed)
├── shared/
│   ├── db/                 ← SQLAlchemy models, session factory
│   ├── llm/                ← Anthropic client wrapper
│   ├── slack/              ← Slack post / parse helpers
│   └── context/            ← Loads knowledge/*.md for prompts
├── knowledge/              ← Markdown knowledge base for Advisor
├── config/                 ← watchlist.yaml (M&A tier 1/2/3)
├── slack-manifests/        ← JSON manifests for the 3 Slack apps
├── scripts/                ← gcloud provisioning + deploy
├── migrations/             ← Alembic
└── .github/workflows/      ← CI + deploy
```

---

## Setup at a glance

Full guide in [`DEPLOY.md`](DEPLOY.md). Quick version:

1. `./scripts/provision.sh` — creates Cloud SQL, Secret Manager entries, Artifact Registry, service account
2. Fill the API key secrets (SerpAPI, Parallel, Anthropic, Slack bot tokens) via `gcloud secrets versions add`
3. Install the Slack apps from `slack-manifests/*.json` — paste each into Slack API → Create New App → From a manifest
4. `./scripts/deploy-monitor.sh` — builds container, deploys Cloud Run job, sets up daily Cloud Scheduler
5. `gcloud run jobs execute monitor-daily --region=us-central1` to verify

Everything's idempotent — re-running scripts is safe.

---

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in keys + local DATABASE_URL
# Spin up local Postgres (or use Cloud SQL Proxy)
alembic upgrade head
python -m monitor.main --dry-run --max-queries 3
```

---

## Phasing

- **Phase 1 (this commit):** Monitor on Postgres, GCP provisioned, all 3 Slack manifests ready, Advisor/Engagement stubbed.
- **Phase 2 (next):** Advisor v1 — Sonnet, knowledge base loading, onboarding flow with Anabella in DM.
- **Phase 3:** Engagement v1 — news-based opportunity surfacing, reuses Monitor's signal stream.
- **Phase 4:** Engagement v2 — conference scraping (HolonIQ, ASU+GSV, BETT, etc.).
- **Phase 5:** Cross-agent triggers — Advisor auto-comments on Tier 1 Monitor alerts.

---

## Cost target

~$15–25/month for GCP + Anthropic combined. Current breakdown in `DEPLOY.md`.
