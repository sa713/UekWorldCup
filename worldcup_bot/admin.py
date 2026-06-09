from __future__ import annotations

import re

from worldcup_bot.constants import PREDICTION_DRAW, PREDICTION_TEAM1, PREDICTION_TEAM2


SCORE_PATTERN = re.compile(r"^\s*(\d{1,2})\s*:\s*(\d{1,2})\s*$")


def is_admin_username(username: str | None, admin_username: str | None) -> bool:
    if not username or not admin_username:
        return False
    return username.casefold() == admin_username.lstrip("@").casefold()


def parse_score(raw_score: str) -> tuple[int, int]:
    match = SCORE_PATTERN.match(raw_score or "")
    if match is None:
        raise ValueError("Введите счет в формате 2:1.")
    return int(match.group(1)), int(match.group(2))


def normalize_score(raw_score: str) -> str:
    goals1, goals2 = parse_score(raw_score)
    return f"{goals1}:{goals2}"


def winner_from_score(raw_score: str) -> str:
    goals1, goals2 = parse_score(raw_score)
    if goals1 > goals2:
        return PREDICTION_TEAM1
    if goals2 > goals1:
        return PREDICTION_TEAM2
    return PREDICTION_DRAW
