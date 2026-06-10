from __future__ import annotations

import pytest

from tests.helpers import add_match, finish_match, set_registration_date


@pytest.mark.asyncio
async def test_leaderboard_sorts_by_rating_bets_count_and_registration_date(db):
    await db.register_user(3001, "Лучший рейтинг")
    await db.register_user(3002, "Больше ставок")
    await db.register_user(3003, "Раньше зарегистрирован")
    await db.register_user(3004, "Позже зарегистрирован")

    await set_registration_date(db, 3001, "2026-01-04T10:00:00+03:00")
    await set_registration_date(db, 3002, "2026-01-03T10:00:00+03:00")
    await set_registration_date(db, 3003, "2026-01-01T10:00:00+03:00")
    await set_registration_date(db, 3004, "2026-01-02T10:00:00+03:00")

    high_match = await add_match(db, team1="A", team2="B")
    more_bets_win = await add_match(db, team1="C", team2="D")
    more_bets_loss = await add_match(db, team1="E", team2="F")
    early_open = await add_match(db, team1="G", team2="H")
    late_open = await add_match(db, team1="I", team2="J")

    await db.save_prediction(3001, high_match, "team1")
    await db.save_prediction(3002, more_bets_win, "team1")
    await db.save_prediction(3002, more_bets_loss, "team1")
    await db.save_prediction(3003, early_open, "team1")
    await db.save_prediction(3004, late_open, "team1")

    await finish_match(db, high_match, score="1:0", winner="team1")
    await finish_match(db, more_bets_win, score="1:0", winner="team1")
    await finish_match(db, more_bets_loss, score="0:1", winner="team2")
    await db.score_finished_matches()

    board = await db.leaderboard()
    assert [row["display_name"] for row in board] == [
        "Лучший рейтинг",
        "Больше ставок",
        "Раньше зарегистрирован",
        "Позже зарегистрирован",
    ]
    assert board[0]["rating"] == 1
    assert board[1]["rating"] == 0
    assert board[1]["bets_count"] == 2
    assert board[2]["rating"] == 0
    assert board[2]["bets_count"] == 0
    assert board[3]["rating"] == 0
    assert board[3]["bets_count"] == 0
