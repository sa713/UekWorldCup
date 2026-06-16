from __future__ import annotations

import pytest

from tests.helpers import add_match


async def add_predictions(db, match_id: int, predictions: list[str], *, first_telegram_id: int) -> None:
    for index, prediction in enumerate(predictions):
        telegram_id = first_telegram_id + index
        await db.register_user(telegram_id, f"Игрок {telegram_id}")
        await db.save_prediction(telegram_id, match_id, prediction)


@pytest.mark.asyncio
async def test_prediction_stats_count_real_predictions_and_ignore_none(db):
    match_id = await add_match(db)
    await add_predictions(
        db,
        match_id,
        ["team1", "team1", "team1", "draw", "none", "none"],
        first_telegram_id=6001,
    )
    await db.register_user(7001, "Без прогноза")

    stats = await db.get_prediction_stats_for_matches([match_id])

    assert stats[match_id] == {"team1": 75, "draw": 25, "team2": 0}


@pytest.mark.asyncio
async def test_prediction_stats_truncate_fractional_percentages(db):
    match_id = await add_match(db)
    await add_predictions(
        db,
        match_id,
        ["team1", "team1", "draw"],
        first_telegram_id=6101,
    )

    stats = await db.get_prediction_stats_for_matches([match_id])

    assert stats[match_id] == {"team1": 66, "draw": 33, "team2": 0}


@pytest.mark.asyncio
async def test_prediction_stats_return_zeroes_without_real_predictions(db):
    match_id = await add_match(db)
    await add_predictions(db, match_id, ["none"], first_telegram_id=6201)

    stats = await db.get_prediction_stats_for_matches([match_id])

    assert stats[match_id] == {"team1": 0, "draw": 0, "team2": 0}


@pytest.mark.asyncio
async def test_prediction_stats_handle_multiple_matches(db):
    first_match_id = await add_match(db, team1="Испания", team2="Кабо-Верде")
    second_match_id = await add_match(db, team1="Бельгия", team2="Египет")
    await add_predictions(
        db,
        first_match_id,
        ["team1", "draw", "team2", "team2"],
        first_telegram_id=6301,
    )
    await add_predictions(
        db,
        second_match_id,
        ["team1", "team1", "team1", "draw", "none", "none"],
        first_telegram_id=6401,
    )

    stats = await db.get_prediction_stats_for_matches([first_match_id, second_match_id])

    assert stats[first_match_id] == {"team1": 25, "draw": 25, "team2": 50}
    assert stats[second_match_id] == {"team1": 75, "draw": 25, "team2": 0}
