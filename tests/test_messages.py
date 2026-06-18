from __future__ import annotations

from zoneinfo import ZoneInfo

from worldcup_bot.constants import GROUP, PLAYOFF
from worldcup_bot.keyboards import prediction_keyboard
from worldcup_bot.messages import (
    REGISTRATION_PROMPT,
    UPCOMING_MATCHES_HEADER,
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


def test_upcoming_matches_header_mentions_channel_and_uses_two_paragraphs():
    assert UPCOMING_MATCHES_HEADER == (
        "Результаты и рейтинг – в канале @uekworldcup\n\n"
        "Ближайшие матчи:"
    )
    assert UPCOMING_MATCHES_HEADER.split("\n\n") == [
        "Результаты и рейтинг – в канале @uekworldcup",
        "Ближайшие матчи:",
    ]


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


def test_leaderboard_rows_show_points_without_bets_count():
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

    assert "1. Сергей — 4 (+7 / -3)" in personal_text
    assert "Сергей" in channel_text
    assert "Сергей — рейтинг" not in personal_text
    assert "Сергей — рейтинг" not in channel_text
    assert "ставок" not in personal_text
    assert "ставок" not in channel_text


def test_registration_prompt_contains_updated_intro():
    paragraphs = REGISTRATION_PROMPT.split("\n\n")

    assert paragraphs == [
        "Привет!",
        "Это бот конкурса прогнозов УЭК на матчи Чемпионата мира по футболу 2026.",
        (
            "Правила простые – я присылаю ближайшие матчи, ты делаешь прогнозы, раз в сутки "
            "в канале @uekworldcup я публикую результаты матчей и рейтинг участников конкурса. "
            "За верный прогноз начисляется 1 балл, за неверный – снимается 1 балл. "
            "В случае пропуска прогноза (участник не успел сделать до начала матча или нажал вариант skip) "
            "баллы не начисляются и не снимаются. Победитель конкурса получит приятный сюрприз."
        ),
        (
            "Прогнозы делаются на каждый матч отдельно. Чтобы сделать прогноз, нужно нажать на кнопку под матчем "
            "(я буду присылать расписание):\n"
            "- 1 – победа команды 1\n"
            "- X – ничья\n"
            "- 2 – победа команды 2\n"
            "- skip – не делать прогноз"
        ),
        "Пожалуйста, укажи своё имя или ник для отображения в рейтинге.",
    ]
    assert "бот конкурса прогнозов УЭК" in REGISTRATION_PROMPT
    assert "@uekworldcup" in REGISTRATION_PROMPT
    assert "skip" in REGISTRATION_PROMPT
    assert paragraphs[-1] == "Пожалуйста, укажи своё имя или ник для отображения в рейтинге."
