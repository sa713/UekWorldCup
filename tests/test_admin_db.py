from __future__ import annotations

import pytest

from worldcup_bot.constants import FINISHED, LOCKED, PLAYOFF, SCHEDULED, SCORED
from worldcup_bot.db import MatchResultError

from tests.helpers import add_match


@pytest.mark.asyncio
async def test_update_match_result_sets_score_winner_and_finished_status(db):
    match_id = await add_match(db, status=LOCKED)

    match = await db.update_match_result(match_id, "2:1", "team1")

    assert match["status"] == FINISHED
    assert match["score"] == "2:1"
    assert match["winner"] == "team1"
    assert match["result_recorded_at"] is not None


@pytest.mark.asyncio
async def test_update_match_result_rejects_playoff_draw(db):
    match_id = await add_match(
        db,
        stage="1/8 финала",
        match_type=PLAYOFF,
        status=LOCKED,
    )

    with pytest.raises(MatchResultError, match="плей-офф ничья невозможна"):
        await db.update_match_result(match_id, "1:1", "draw")

    assert (await db.get_match(match_id))["status"] == LOCKED


@pytest.mark.asyncio
async def test_update_match_result_rejects_scored_match(db):
    match_id = await add_match(db, status=SCORED)

    with pytest.raises(MatchResultError, match="Матч уже обработан"):
        await db.update_match_result(match_id, "2:1", "team1")


@pytest.mark.asyncio
async def test_reset_test_data_keeps_schedule_and_clears_competition_data(db):
    first_match = await add_match(db)
    second_match = await add_match(db, team1="A", team2="B", status=FINISHED)
    await db.register_user(5001, "Тестовый участник")
    await db.save_prediction(5001, first_match, "team1")
    await db.update_match_result(first_match, "1:0", "team1")
    await db.score_finished_matches()
    await db.set_setting("temporary", "value")

    await db.reset_test_data()

    conn = db._connection()
    for table_name in ("users", "predictions", "score_events", "settings"):
        async with conn.execute(f"SELECT COUNT(*) AS count FROM {table_name}") as cursor:
            assert (await cursor.fetchone())["count"] == 0

    async with conn.execute("SELECT COUNT(*) AS count FROM matches") as cursor:
        assert (await cursor.fetchone())["count"] == 2

    first = await db.get_match(first_match)
    second = await db.get_match(second_match)
    assert first["status"] == SCHEDULED
    assert first["score"] is None
    assert first["winner"] is None
    assert first["result_recorded_at"] is None
    assert second["status"] == SCHEDULED
