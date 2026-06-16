from __future__ import annotations

import logging
from datetime import timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from worldcup_bot.config import Config
from worldcup_bot.db import Database
from worldcup_bot.keyboards import prediction_keyboard
from worldcup_bot.messages import format_match_card
from worldcup_bot.publisher import publish_channel_summary
from worldcup_bot.timeutils import iso_now, now_in_tz


logger = logging.getLogger(__name__)
LAST_CHANNEL_SUMMARY_KEY = "last_channel_summary_at"


async def lock_due_matches_job(db: Database) -> None:
    locked = await db.lock_due_matches()
    if locked:
        logger.info("Locked %s matches", len(locked))


async def score_finished_matches_job(db: Database) -> None:
    scored = await db.score_finished_matches()
    if scored:
        logger.info("Scored %s matches", len(scored))


async def send_daily_upcoming_job(bot: Bot, db: Database, config: Config) -> None:
    users = await db.list_users()
    if not users:
        logger.info("Daily upcoming skipped: no registered users")
        return

    matches = await db.list_upcoming_matches(days=config.upcoming_days, limit=20)
    for user in users:
        chat_id = user["telegram_id"]
        try:
            if not matches:
                await bot.send_message(chat_id, "Ближайших матчей с открытыми прогнозами пока нет.")
                continue

            await bot.send_message(chat_id, "Ближайшие матчи на сегодня и ближайшие дни:")
            for match in matches:
                selected = await db.get_user_prediction(chat_id, match["id"])
                await bot.send_message(
                    chat_id,
                    format_match_card(match, db.tz, selected),
                    reply_markup=prediction_keyboard(match, selected),
                )
        except TelegramAPIError:
            logger.exception("Failed to send daily upcoming message to user %s", chat_id)


async def publish_daily_summary_job(bot: Bot, db: Database, config: Config) -> None:
    if config.channel_id is None:
        logger.info("Channel summary skipped: CHANNEL_ID is not configured")
        return

    last_summary_at = await db.get_setting(LAST_CHANNEL_SUMMARY_KEY)
    if last_summary_at is None:
        last_summary_at = (now_in_tz(db.tz) - timedelta(days=config.results_lookback_days)).isoformat(
            timespec="seconds"
        )

    results = await db.list_results_since(last_summary_at)
    leaderboard = await db.leaderboard()
    prediction_stats = await db.get_prediction_stats_for_matches([int(match["id"]) for match in results])

    try:
        await publish_channel_summary(bot, config.channel_id, results, leaderboard, prediction_stats)
    except TelegramAPIError:
        logger.exception("Failed to publish channel summary")
        return

    await db.set_setting(LAST_CHANNEL_SUMMARY_KEY, iso_now(db.tz))


async def bootstrap_scheduler_settings(db: Database, config: Config) -> None:
    initial_summary_time = (
        now_in_tz(db.tz) - timedelta(days=config.results_lookback_days)
    ).isoformat(timespec="seconds")
    await db.seed_setting_if_missing(LAST_CHANNEL_SUMMARY_KEY, initial_summary_time)


def create_scheduler(bot: Bot, db: Database, config: Config) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=db.tz)

    scheduler.add_job(
        lock_due_matches_job,
        "interval",
        minutes=config.lock_interval_minutes,
        args=[db],
        id="lock_due_matches",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        score_finished_matches_job,
        "interval",
        minutes=config.scoring_interval_minutes,
        args=[db],
        id="score_finished_matches",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        send_daily_upcoming_job,
        "cron",
        hour=config.daily_users_hour,
        minute=config.daily_users_minute,
        args=[bot, db, config],
        id="send_daily_upcoming",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        publish_daily_summary_job,
        "cron",
        hour=config.daily_channel_hour,
        minute=config.daily_channel_minute,
        args=[bot, db, config],
        id="publish_daily_summary",
        replace_existing=True,
        max_instances=1,
    )

    return scheduler
