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


def test_leaderboard_display_places_are_dense_by_rating_only():
    rows = [
        leaderboard_row("Иван", 5, 5, 0, 3),
        leaderboard_row("Пётр", 3, 4, -1, 8),
        leaderboard_row("Анна", 3, 3, 0, 2),
        leaderboard_row("Сергей", 1, 2, -1, 5),
    ]

    placed_rows = leaderboard_rows_with_places(rows)

    assert [row["place"] for row in placed_rows] == [1, 2, 2, 3]
    assert placed_rows[1]["place"] == placed_rows[2]["place"]


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
