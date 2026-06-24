"""Slack helpers using Bot Token (chat:write).

Three agents will each have their own bot token; pass it in explicitly.
Webhooks would also work for Monitor, but bot tokens unify the API for all
three agents and let the Advisor receive events too.
"""
from __future__ import annotations
import os
from typing import Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from shared.db import get_session, BotPost


class SlackPoster:
    def __init__(self, bot_token: str, channel_id: str, agent: str):
        self.client = WebClient(token=bot_token)
        self.channel_id = channel_id
        self.agent = agent

    def post(
        self,
        text: str,
        *,
        thread_ts: Optional[str] = None,
        related_extraction_id=None,
        related_target_id=None,
    ) -> Optional[str]:
        """Post a message. Returns the message ts on success, None on failure.
        Records the post in bot_posts for cross-agent context.
        """
        try:
            resp = self.client.chat_postMessage(
                channel=self.channel_id,
                text=text,
                thread_ts=thread_ts,
                unfurl_links=False,
                unfurl_media=False,
            )
            ts = resp["ts"]
        except SlackApiError as e:
            print(f"[slack:{self.agent}] error: {e.response.get('error')}")
            return None

        # Audit log — best-effort, doesn't block on DB failure
        try:
            with get_session() as s:
                s.add(BotPost(
                    agent=self.agent,
                    slack_channel_id=self.channel_id,
                    slack_message_ts=ts,
                    payload={"text": text, "thread_ts": thread_ts},
                    related_extraction_id=related_extraction_id,
                    related_target_id=related_target_id,
                ))
        except Exception as e:
            print(f"[slack:{self.agent}] audit log failed: {e}")

        return ts


def poster_from_env(agent: str) -> SlackPoster:
    token = os.getenv("SLACK_BOT_TOKEN")
    channel = os.getenv("SLACK_CHANNEL_ID")
    if not token or not channel:
        raise RuntimeError(f"SLACK_BOT_TOKEN / SLACK_CHANNEL_ID not set for {agent}")
    return SlackPoster(token, channel, agent)
