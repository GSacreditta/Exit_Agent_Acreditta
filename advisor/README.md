# Advisor — Phase 2

M&A coach for Anabella. Sonnet-backed. Lives as a Cloud Run service receiving Slack Events API webhooks.

## Status

**Stubbed.** Phase 1 ships the package structure; Phase 2 implements:

- FastAPI app handling `app_mention` and `message.im` events
- Loads `shared.context.context_block()` + relevant knowledge files on each call
- Pulls recent Monitor signals from DB to inform answers
- Maintains `coaching_threads` rows for memory
- Onboarding DM flow when Anabella first messages the bot
- Hard rules: no legal advice, no replacement for transaction advisor

## What's here in Phase 1

- `main.py` — placeholder; raises if invoked
- This README

## Phase 2 plan

1. FastAPI app + Slack request signature verification
2. Onboarding flow (already drafted; lives in `prompts.py`)
3. System prompt builder that loads context + recent signals
4. Sonnet call with conversation memory from `coaching_threads`
5. Dockerfile + `scripts/deploy-advisor.sh`
6. Slack manifest URL update + redeploy
