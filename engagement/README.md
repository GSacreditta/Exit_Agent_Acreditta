# Engagement — Phase 3

Outreach opportunity tracker. Reuses Monitor's signal stream; surfaces moments when a tracked decision-maker appears in news or speaks at a conference.

## Status

**Stubbed.** Phase 3 implements:

- Daily scheduled job (separate from Monitor cron) that queries `extractions` joined with `engagement_targets` to find recent signals on tracked contacts
- FastAPI service handling `/engaged` and `/snooze` slash commands
- Slack interactivity (buttons on opportunity messages)
- Draft message generation (1 LLM call per opportunity)

## Phase 4 adds

- Per-conference scrapers — HolonIQ Summit, ASU+GSV, BETT LATAM, HR Tech, Unleash, EdTech Brasil
- Conference watchlist YAML
- Multi-source signal fusion (news + speaker lists + LinkedIn announcements when flagged)
