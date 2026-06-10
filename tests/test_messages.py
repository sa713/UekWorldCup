from __future__ import annotations

from zoneinfo import ZoneInfo

from worldcup_bot.constants import GROUP, PLAYOFF
from worldcup_bot.keyboards import prediction_keyboard
from worldcup_bot.messages import (
    REGISTRATION_PROMPT,
    format_channel_summary,
    format_leaderboard,
    format_match_card,
)


def test_format_match_card_uses_compact_forecast_text():
    tz = ZoneInfo("Europe/Moscow")
    text = format_match_card(
        {
            "team1": "Южная Корея",
            "team2": "Чехия",
            "stage": "Групповой этап",
            "match_type": GROUP,
            "group_name": "A",
            "kickoff_time": "2026-06-12T06:00:00+03:00",
        },
        tz,
    )

    assert text == "12 июня, 06:00 | Южная Корея – Чехия"
    assert "Стадия:" not in text
    assert "Группа:" not in text
    assert "Начало:" not in text


def test_prediction_keyboard_uses_short_labels():
    group_keyboard = prediction_keyboard(
        {
            "id": 10,
            "team1": "Мексика",
            "team2": "ЮАР",
            "match_type": GROUP,
        }
    )
    playoff_keyboard = prediction_keyboard(
        {
            "id": 11,
            "team1": "Бразилия",
            "team2": "Франция",
            "match_type": PLAYOFF,
        }
    )

    assert [button.text for button in group_keyboard.inline_keyboard[0]] == ["1", "X", "2", "skip"]
    assert group_keyboard.inline_keyboard[0][-1].callback_data == "pred:10:none"
    assert [button.text for button in playoff_keyboard.inline_keyboard[0]] == ["1", "2", "skip"]
    assert playoff_keyboard.inline_keyboard[0][-1].callback_data == "pred:11:none"


def test_leaderboard_rows_do_not_repeat_rating_word():
    rows = [
        {
            "display_name": "Сергей",
            "rating": 4,
            "positive_points": 7,
            "negative_points": -3,
            "bets_count": 10,
        }
    ]

    personal_text = format_leaderboard(rows)
    channel_text = format_channel_summary([], rows)

    assert "1. Сергей — 4 (+7 / -3) — 10 ставок" in personal_text
    assert "Сергей — 4 (+7 / -3) — 10 ставок" in channel_text
    assert "Сергей — рейтинг" not in personal_text
    assert "Сергей — рейтинг" not in channel_text


def test_registration_prompt_contains_updated_intro():
    assert "бот конкурса прогнозов УЭК" in REGISTRATION_PROMPT
    assert "@uekworldcup" in REGISTRATION_PROMPT
    assert "Пожалуйста, укажи своё имя или ник" in REGISTRATION_PROMPT
