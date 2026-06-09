from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    channel_id: int | str | None
    timezone: str
    database_path: Path
    daily_users_hour: int
    daily_users_minute: int
    daily_channel_hour: int
    daily_channel_minute: int
    upcoming_days: int
    results_lookback_days: int
    lock_interval_minutes: int
    scoring_interval_minutes: int


def _get_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    return int(raw_value)


def _get_channel_id(raw_value: str) -> int | str | None:
    value = raw_value.strip()
    if not value:
        return None
    if value.lstrip("-").isdigit():
        return int(value)
    return value


def load_config(env_file: str | Path = ".env", *, require_bot_token: bool = True) -> Config:
    load_dotenv(env_file)

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if require_bot_token and not bot_token:
        raise RuntimeError("BOT_TOKEN is required. Put it into .env or the environment.")

    return Config(
        bot_token=bot_token,
        channel_id=_get_channel_id(os.getenv("CHANNEL_ID", "")),
        timezone=os.getenv("TIMEZONE", "Europe/Moscow").strip() or "Europe/Moscow",
        database_path=Path(os.getenv("DATABASE_PATH", "data/worldcup.sqlite3")),
        daily_users_hour=_get_int("DAILY_USERS_HOUR", 10),
        daily_users_minute=_get_int("DAILY_USERS_MINUTE", 0),
        daily_channel_hour=_get_int("DAILY_CHANNEL_HOUR", 21),
        daily_channel_minute=_get_int("DAILY_CHANNEL_MINUTE", 0),
        upcoming_days=_get_int("UPCOMING_DAYS", 2),
        results_lookback_days=_get_int("RESULTS_LOOKBACK_DAYS", 2),
        lock_interval_minutes=_get_int("LOCK_INTERVAL_MINUTES", 1),
        scoring_interval_minutes=_get_int("SCORING_INTERVAL_MINUTES", 5),
    )
