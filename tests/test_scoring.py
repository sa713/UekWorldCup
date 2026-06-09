from __future__ import annotations

import pytest

from worldcup_bot.constants import SCORED

from tests.helpers import add_match, by_name, finish_match, score_events


@pytest.mark.asyncio
async def test_group_match_scores_correct_wrong_and_ignores_none(db):
    match_id = await add_match(
        db,
        team1="Аргентина",
        team2="Франция",
        stage="Групповой этап",
        match_type="group",
    )
    await db.register_user(1001, "Верный")
    await db.register_user(1002, "Неверный")
    await db.register_user(1003, "Ничья")
    await db.register_user(1004, "Без прогноза")

    await db.save_prediction(1001, match_id, "team1")
    await db.save_prediction(1002, match_id, "team2")
    await db.save_prediction(1003, match_id, "draw")
    await db.save_prediction(1004, match_id, "none")

    await finish_match(db, match_id, score="2:1", winner="team1")
    scored = await db.score_finished_matches()

    assert scored == [{"match_id": match_id, "events": 3}]
    assert (await db.get_match(match_id))["status"] == SCORED

    events = await score_events(db)
    assert len(events) == 3
    assert {event["telegram_id"]: event["points"] for event in events} == {
        1001: 1,
        1002: -1,
        1003: -1,
    }

    board = by_name(await db.leaderboard())
    assert board["Верный"]["rating"] == 1
    assert board["Верный"]["bets_count"] == 1
    assert board["Неверный"]["rating"] == -1
    assert board["Ничья"]["rating"] == -1
    assert board["Без прогноза"]["rating"] == 0
    assert board["Без прогноза"]["bets_count"] == 0
