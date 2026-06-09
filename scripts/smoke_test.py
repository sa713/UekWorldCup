from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from worldcup_bot.constants import SCORED  # noqa: E402
from worldcup_bot.db import Database, PredictionError  # noqa: E402


async def add_match(
    db: Database,
    *,
    team1: str,
    team2: str,
    stage: str,
    match_type: str,
    kickoff_time: str = "2099-06-14T21:00:00+03:00",
) -> int:
    conn = db._connection()
    cursor = await conn.execute(
        """
        INSERT INTO matches (team1, team2, stage, match_type, kickoff_time, status)
        VALUES (?, ?, ?, ?, ?, 'scheduled')
        """,
        (team1, team2, stage, match_type, kickoff_time),
    )
    await conn.commit()
    return int(cursor.lastrowid)


async def finish_match(db: Database, match_id: int, *, score: str, winner: str) -> None:
    conn = db._connection()
    await conn.execute(
        """
        UPDATE matches
        SET status = 'finished', score = ?, winner = ?
        WHERE id = ?
        """,
        (score, winner, match_id),
    )
    await conn.commit()


async def main() -> int:
    with tempfile.TemporaryDirectory(prefix="uek-worldcup-") as tmp_dir:
        db = Database(Path(tmp_dir) / "smoke.sqlite3", "Europe/Moscow")
        await db.connect()
        await db.init_schema()

        try:
            group_match = await add_match(
                db,
                team1="Аргентина",
                team2="Франция",
                stage="Групповой этап",
                match_type="group",
            )
            playoff_match = await add_match(
                db,
                team1="Бразилия",
                team2="Нидерланды",
                stage="1/8 финала",
                match_type="playoff",
            )

            await db.register_user(1001, "Сергей")
            await db.register_user(1002, "Ольга")
            await db.register_user(1003, "Нина")

            await db.save_prediction(1001, group_match, "team1")
            await db.save_prediction(1002, group_match, "team2")
            await db.save_prediction(1003, group_match, "none")

            await db.save_prediction(1001, playoff_match, "team1")
            await db.save_prediction(1002, playoff_match, "team2")
            await db.save_prediction(1003, playoff_match, "team2")

            try:
                await db.save_prediction(1003, playoff_match, "draw")
            except PredictionError:
                pass
            else:
                raise AssertionError("Playoff draw prediction must be rejected")

            await finish_match(db, group_match, score="2:1", winner="team1")
            await finish_match(db, playoff_match, score="0:1", winner="team2")

            scored = await db.score_finished_matches()
            assert len(scored) == 2
            assert (await db.get_match(group_match))["status"] == SCORED
            assert (await db.get_match(playoff_match))["status"] == SCORED

            leaderboard = await db.leaderboard()
            by_name = {row["display_name"]: row for row in leaderboard}
            assert by_name["Сергей"]["rating"] == 0
            assert by_name["Ольга"]["rating"] == 0
            assert by_name["Нина"]["rating"] == 1
            assert by_name["Нина"]["bets_count"] == 1

            print("Smoke-test passed. Итоговый рейтинг:")
            for index, row in enumerate(leaderboard, start=1):
                print(
                    (
                        f"{index}. {row['display_name']} — рейтинг {row['rating']} "
                        f"(+{row['positive_points']} / {row['negative_points']}) — "
                        f"{row['bets_count']} ставок"
                    )
                )
            return 0
        finally:
            await db.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
