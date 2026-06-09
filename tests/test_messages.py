from __future__ import annotations

from zoneinfo import ZoneInfo

from worldcup_bot.messages import format_match_card


def test_format_match_card_shows_group_only_for_group_matches():
    tz = ZoneInfo("Europe/Moscow")
    group_text = format_match_card(
        {
            "team1": "Mexico",
            "team2": "South Africa",
            "stage": "Group stage",
            "match_type": "group",
            "group_name": "A",
            "kickoff_time": "2026-06-11T23:00:00+03:00",
        },
        tz,
    )
    playoff_text = format_match_card(
        {
            "team1": "W101",
            "team2": "W102",
            "stage": "Final",
            "match_type": "playoff",
            "group_name": None,
            "kickoff_time": "2026-07-19T23:00:00+03:00",
        },
        tz,
    )

    assert "Группа: A" in group_text
    assert "Группа:" not in playoff_text
