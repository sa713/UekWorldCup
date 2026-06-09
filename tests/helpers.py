from __future__ import annotations

from worldcup_bot.constants import FINISHED, SCHEDULED
from worldcup_bot.db import Database


FUTURE_KICKOFF = "2099-06-14T21:00:00+03:00"
PAST_KICKOFF = "2000-06-14T21:00:00+03:00"


async def add_match(
    db: Database,
    *,
    team1: str = "Команда 1",
    team2: str = "Команда 2",
    stage: str = "Групповой этап",
    match_type: str = "group",
    kickoff_time: str = FUTURE_KICKOFF,
    status: str = SCHEDULED,
) -> int:
    conn = db._connection()
    cursor = await conn.execute(
        """
        INSERT INTO matches (team1, team2, stage, match_type, kickoff_time, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (team1, team2, stage, match_type, kickoff_time, status),
    )
    await conn.commit()
    return int(cursor.lastrowid)


async def finish_match(
    db: Database,
    match_id: int,
    *,
    score: str = "2:1",
    winner: str = "team1",
) -> None:
    conn = db._connection()
    await conn.execute(
        """
        UPDATE matches
        SET status = ?, score = ?, winner = ?
        WHERE id = ?
        """,
        (FINISHED, score, winner, match_id),
    )
    await conn.commit()


async def set_registration_date(db: Database, telegram_id: int, registration_date: str) -> None:
    conn = db._connection()
    await conn.execute(
        "UPDATE users SET registration_date = ? WHERE telegram_id = ?",
        (registration_date, telegram_id),
    )
    await conn.commit()


async def score_events(db: Database) -> list[dict]:
    conn = db._connection()
    async with conn.execute(
        """
        SELECT se.*, u.telegram_id
        FROM score_events se
        JOIN users u ON u.id = se.user_id
        ORDER BY se.id ASC
        """
    ) as cursor:
        return [dict(row) for row in await cursor.fetchall()]


def by_name(rows: list[dict]) -> dict[str, dict]:
    return {row["display_name"]: row for row in rows}
