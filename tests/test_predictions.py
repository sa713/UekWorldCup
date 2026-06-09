from __future__ import annotations

from datetime import timedelta

import aiosqlite
import pytest

from worldcup_bot.constants import LOCKED
from worldcup_bot.db import PredictionError
from worldcup_bot.timeutils import now_in_tz

from tests.helpers import PAST_KICKOFF, add_match, finish_match


@pytest.mark.asyncio
async def test_playoff_accepts_team_winners_and_rejects_draw_prediction(db):
    match_id = await add_match(
        db,
        team1="Бразилия",
        team2="Нидерланды",
        stage="1/8 финала",
        match_type="playoff",
    )
    await db.register_user(2001, "Первый")
    await db.register_user(2002, "Второй")
    await db.register_user(2003, "Любитель ничьих")

    await db.save_prediction(2001, match_id, "team1")
    await db.save_prediction(2002, match_id, "team2")

    with pytest.raises(PredictionError, match="недоступен"):
        await db.save_prediction(2003, match_id, "draw")

    assert await db.get_user_prediction(2001, match_id) == "team1"
    assert await db.get_user_prediction(2002, match_id) == "team2"
    assert await db.get_user_prediction(2003, match_id) is None


@pytest.mark.asyncio
async def test_playoff_draw_result_is_not_scored(db):
    match_id = await add_match(
        db,
        team1="Португалия",
        team2="Уругвай",
        stage="1/4 финала",
        match_type="playoff",
    )
    await db.register_user(2101, "Игрок")
    await db.save_prediction(2101, match_id, "team1")

    with pytest.raises(aiosqlite.IntegrityError):
        await finish_match(db, match_id, score="0:0", winner="draw")

    await db._connection().rollback()
    assert await db.score_finished_matches() == []
    assert (await db.get_match(match_id))["status"] != "scored"


@pytest.mark.asyncio
async def test_prediction_after_kickoff_is_rejected_and_match_gets_locked(db):
    match_id = await add_match(
        db,
        team1="Германия",
        team2="Испания",
        kickoff_time=PAST_KICKOFF,
    )
    await db.register_user(2201, "Опоздавший")

    with pytest.raises(PredictionError, match="уже начался"):
        await db.save_prediction(2201, match_id, "team1")

    assert (await db.get_match(match_id))["status"] == LOCKED
    assert await db.get_user_prediction(2201, match_id) is None


@pytest.mark.asyncio
async def test_future_predictions_are_limited_by_days(db):
    now = now_in_tz(db.tz)
    inside_match_id = await add_match(
        db,
        team1="Ближняя команда 1",
        team2="Ближняя команда 2",
        kickoff_time=(now + timedelta(days=1)).isoformat(timespec="seconds"),
    )
    outside_match_id = await add_match(
        db,
        team1="Дальняя команда 1",
        team2="Дальняя команда 2",
        kickoff_time=(now + timedelta(days=3)).isoformat(timespec="seconds"),
    )
    await db.register_user(2301, "Игрок")

    await db.save_prediction(2301, inside_match_id, "team1")
    await db.save_prediction(2301, outside_match_id, "team2")

    rows = await db.list_future_matches_with_predictions(2301, days=2)

    assert [row["id"] for row in rows] == [inside_match_id]
    assert rows[0]["user_prediction"] == "team1"
