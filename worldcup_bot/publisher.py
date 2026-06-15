from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import aiohttp
from aiogram import Bot

from worldcup_bot.messages import (
    format_channel_summary_fallback_html,
    format_channel_summary_rich_html,
)


logger = logging.getLogger(__name__)


class RichMessagePublishError(RuntimeError):
    pass


@dataclass(frozen=True)
class ChannelSummaryPublishResult:
    mode: str


async def send_rich_message(bot: Bot, chat_id: int | str, rich_html: str) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{bot.token}/sendRichMessage"
    payload = {
        "chat_id": chat_id,
        "rich_message": {
            "html": rich_html,
            "skip_entity_detection": True,
        },
    }
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=payload) as response:
            data = await response.json(content_type=None)
            if response.status >= 400 or not data.get("ok"):
                description = data.get("description") or response.reason
                raise RichMessagePublishError(f"sendRichMessage failed: {description}")
            return data


async def publish_channel_summary(
    bot: Bot,
    chat_id: int | str,
    results: list[dict],
    leaderboard: list[dict],
) -> ChannelSummaryPublishResult:
    rich_html = format_channel_summary_rich_html(results, leaderboard)
    try:
        await send_rich_message(bot, chat_id, rich_html)
        return ChannelSummaryPublishResult(mode="rich")
    except (aiohttp.ClientError, RichMessagePublishError, ValueError, asyncio.TimeoutError) as error:
        logger.warning("Rich channel summary failed; falling back to text message: %s", error)

    await bot.send_message(
        chat_id,
        format_channel_summary_fallback_html(results, leaderboard),
        parse_mode="HTML",
    )
    return ChannelSummaryPublishResult(mode="fallback")
