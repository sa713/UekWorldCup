from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


MOSCOW_TZ_NAME = "Europe/Moscow"


def get_timezone(name: str | None) -> ZoneInfo:
    return ZoneInfo(name or MOSCOW_TZ_NAME)


def now_in_tz(tz: ZoneInfo) -> datetime:
    return datetime.now(tz)


def iso_now(tz: ZoneInfo) -> str:
    return now_in_tz(tz).isoformat(timespec="seconds")


def parse_datetime(value: str, tz: ZoneInfo) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"

    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return parsed.astimezone(tz)


def format_moscow_datetime(value: str, tz: ZoneInfo) -> str:
    return parse_datetime(value, tz).strftime("%d.%m.%Y %H:%M")
