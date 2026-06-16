from __future__ import annotations

import pytest

from worldcup_bot.messages import (
    format_channel_summary,
    format_channel_summary_rich_html,
    format_leaderboard_table_text,
    leaderboard_rows_with_places,
)
from worldcup_bot.publisher import RichMessagePublishError, publish_channel_summary


def leaderboard_row(
    display_name: str,
    rating: int,
    positive_points: int,
    negative_points: int,
    bets_count: int = 0,
) -> dict:
    return {
        "display_name": display_name,
        "rating": rating,
        "positive_points": positive_points,
        "negative_points": negative_points,
        "bets_count": bets_count,
    }


def test_leaderboard_display_places_use_full_rank_key():
    rows = [
        leaderboard_row("Stnbrl", -2, 7, -9),
        leaderboard_row("🅴🆉", -2, 4, -6),
        leaderboard_row("Денис", -2, 1, -3),
    ]

    placed_rows = leaderboard_rows_with_places(rows)

    assert [row["place"] for row in placed_rows] == [1, 2, 3]


def test_leaderboard_display_places_split_equal_rating_by_processed_bets():
    rows = [
        leaderboard_row("Больше обработанных", 0, 6, -6),
        leaderboard_row("Меньше обработанных", 0, 6, -4),
    ]

    placed_rows = leaderboard_rows_with_places(rows)

    assert [row["place"] for row in placed_rows] == [1, 2]


def test_leaderboard_display_places_share_full_tie_and_skip_next_number():
    rows = [
        leaderboard_row("Stnbrl", -2, 7, -9),
        leaderboard_row("Alex", -2, 7, -9),
        leaderboard_row("Денис", -2, 1, -3),
    ]

    placed_rows = leaderboard_rows_with_places(rows)

    assert [row["place"] for row in placed_rows] == [1, 1, 3]
    assert placed_rows[0]["place"] == placed_rows[1]["place"]


def test_negative_points_column_is_rendered_without_minus():
    table = format_leaderboard_table_text([leaderboard_row("Всеволод Бобров", -2, 5, -7)])
    participant_line = table.splitlines()[1]

    assert participant_line.split("|")[-1].strip() == "7"
    assert "-7" not in table


def test_channel_summary_tables_have_expected_columns():
    rows = [leaderboard_row("sa", 0, 6, -6)]

    fallback_text = format_channel_summary([], rows)
    rich_html = format_channel_summary_rich_html([], rows)

    for column_name in ("Место", "Участник", "Очки", "+", "-"):
        assert column_name in fallback_text
        assert f"<th>{column_name}</th>" in rich_html
    assert "<table" in rich_html


def test_channel_summary_results_include_prediction_stats_with_blank_line_between_matches():
    results = [
        {"id": 1, "team1": "Испания", "score": "0:0", "team2": "Кабо-Верде"},
        {"id": 2, "team1": "Бельгия", "score": "1:1", "team2": "Египет"},
    ]
    stats = {
        1: {"team1": 50, "draw": 0, "team2": 50},
        2: {"team1": 75, "draw": 25, "team2": 0},
    }

    text = format_channel_summary(results, [], stats)
    rich_html = format_channel_summary_rich_html(results, [], stats)

    assert "- Испания 0:0 Кабо-Верде\n(50 – 0 – 50)\n\n- Бельгия 1:1 Египет\n(75 – 25 – 0)" in text
    assert "- Испания 0:0 Кабо-Верде<br>(50 – 0 – 50)" in rich_html
    assert "- Бельгия 1:1 Египет<br>(75 – 25 – 0)" in rich_html


def test_channel_summary_results_show_zero_stats_when_predictions_are_absent():
    results = [{"id": 1, "team1": "Испания", "score": "0:0", "team2": "Кабо-Верде"}]

    text = format_channel_summary(results, [], {})

    assert "(0 – 0 – 0)" in text


def test_fallback_table_has_no_medal_emojis():
    text = format_channel_summary([], [leaderboard_row("🅴🆉", 1, 4, -3)])

    assert "🥇" not in text
    assert "🥈" not in text
    assert "🥉" not in text


@pytest.mark.asyncio
async def test_publish_channel_summary_falls_back_to_html_text(monkeypatch):
    class FakeBot:
        def __init__(self) -> None:
            self.sent_messages = []

        async def send_message(self, chat_id, text, parse_mode=None):
            self.sent_messages.append(
                {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                }
            )

    async def fail_rich_message(bot, chat_id, rich_html):
        raise RichMessagePublishError("not supported")

    fake_bot = FakeBot()
    monkeypatch.setattr("worldcup_bot.publisher.send_rich_message", fail_rich_message)

    result = await publish_channel_summary(fake_bot, "@channel", [], [leaderboard_row("sa", 0, 6, -6)])

    assert result.mode == "fallback"
    assert fake_bot.sent_messages[0]["chat_id"] == "@channel"
    assert fake_bot.sent_messages[0]["parse_mode"] == "HTML"
    assert "<pre>" in fake_bot.sent_messages[0]["text"]
