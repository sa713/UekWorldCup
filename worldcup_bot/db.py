from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import aiosqlite

from worldcup_bot.constants import (
    FINISHED,
    GROUP,
    LOCKED,
    PLAYOFF,
    PREDICTION_DRAW,
    PREDICTION_NONE,
    SCORED,
    SCHEDULED,
    VALID_PREDICTIONS,
)
from worldcup_bot.timeutils import get_timezone, iso_now, now_in_tz, parse_datetime


class PredictionError(ValueError):
    """Raised when a prediction cannot be saved."""


class MatchResultError(ValueError):
    """Raised when a match result cannot be updated."""


class Database:
    def __init__(self, path: str | Path, timezone_name: str) -> None:
        self.path = Path(path)
        self.tz: ZoneInfo = get_timezone(timezone_name)
        self.conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self.conn.commit()

    async def close(self) -> None:
        if self.conn is not None:
            await self.conn.close()
            self.conn = None

    def _connection(self) -> aiosqlite.Connection:
        if self.conn is None:
            raise RuntimeError("Database is not connected")
        return self.conn

    async def init_schema(self) -> None:
        conn = self._connection()
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                registration_date TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team1 TEXT NOT NULL,
                team2 TEXT NOT NULL,
                stage TEXT NOT NULL,
                group_name TEXT,
                match_type TEXT NOT NULL CHECK (match_type IN ('group', 'playoff')),
                kickoff_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'scheduled'
                    CHECK (status IN ('scheduled', 'locked', 'finished', 'scored')),
                score TEXT,
                winner TEXT CHECK (winner IN ('team1', 'draw', 'team2') OR winner IS NULL),
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                result_recorded_at TEXT,
                CHECK (match_type = 'group' OR winner IS NULL OR winner != 'draw')
            );

            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
                prediction TEXT NOT NULL CHECK (prediction IN ('team1', 'draw', 'team2', 'none')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE (user_id, match_id)
            );

            CREATE TABLE IF NOT EXISTS score_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
                prediction TEXT NOT NULL CHECK (prediction IN ('team1', 'draw', 'team2')),
                result TEXT NOT NULL CHECK (result IN ('team1', 'draw', 'team2')),
                points INTEGER NOT NULL CHECK (points IN (-1, 1)),
                created_at TEXT NOT NULL,
                UNIQUE (user_id, match_id)
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
            CREATE INDEX IF NOT EXISTS idx_matches_kickoff_time ON matches(kickoff_time);
            CREATE INDEX IF NOT EXISTS idx_predictions_user ON predictions(user_id);
            CREATE INDEX IF NOT EXISTS idx_predictions_match ON predictions(match_id);
            CREATE INDEX IF NOT EXISTS idx_score_events_user ON score_events(user_id);
            CREATE INDEX IF NOT EXISTS idx_score_events_match ON score_events(match_id);

            CREATE TRIGGER IF NOT EXISTS trg_matches_updated_at
            AFTER UPDATE ON matches
            FOR EACH ROW
            WHEN NEW.updated_at = OLD.updated_at
            BEGIN
                UPDATE matches
                SET updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
                WHERE id = NEW.id;
            END;

            CREATE TRIGGER IF NOT EXISTS trg_matches_result_recorded_at_update
            AFTER UPDATE OF status, score, winner ON matches
            FOR EACH ROW
            WHEN NEW.status IN ('finished', 'scored')
                AND NEW.score IS NOT NULL
                AND NEW.winner IS NOT NULL
                AND NEW.result_recorded_at IS NULL
            BEGIN
                UPDATE matches
                SET result_recorded_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
                WHERE id = NEW.id;
            END;

            CREATE TRIGGER IF NOT EXISTS trg_matches_result_recorded_at_insert
            AFTER INSERT ON matches
            FOR EACH ROW
            WHEN NEW.status IN ('finished', 'scored')
                AND NEW.score IS NOT NULL
                AND NEW.winner IS NOT NULL
                AND NEW.result_recorded_at IS NULL
            BEGIN
                UPDATE matches
                SET result_recorded_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
                WHERE id = NEW.id;
            END;
            """
        )
        await self._ensure_matches_group_name_column()
        await conn.commit()

    async def _ensure_matches_group_name_column(self) -> None:
        conn = self._connection()
        async with conn.execute("PRAGMA table_info(matches)") as cursor:
            columns = {str(row["name"]) for row in await cursor.fetchall()}
        if "group_name" not in columns:
            await conn.execute("ALTER TABLE matches ADD COLUMN group_name TEXT")

    @staticmethod
    def _dict(row: aiosqlite.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return dict(row)

    async def register_user(self, telegram_id: int, display_name: str) -> dict[str, Any]:
        conn = self._connection()
        now = iso_now(self.tz)
        await conn.execute(
            """
            INSERT INTO users (telegram_id, display_name, registration_date)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET display_name = excluded.display_name
            """,
            (telegram_id, display_name.strip(), now),
        )
        await conn.commit()
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            raise RuntimeError("User registration failed")
        return user

    async def get_user_by_telegram_id(self, telegram_id: int) -> dict[str, Any] | None:
        conn = self._connection()
        async with conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,),
        ) as cursor:
            return self._dict(await cursor.fetchone())

    async def list_users(self) -> list[dict[str, Any]]:
        conn = self._connection()
        async with conn.execute("SELECT * FROM users ORDER BY registration_date ASC") as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def get_match(self, match_id: int) -> dict[str, Any] | None:
        conn = self._connection()
        async with conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,)) as cursor:
            return self._dict(await cursor.fetchone())

    async def list_matches_for_result_entry(self, *, limit: int = 20) -> list[dict[str, Any]]:
        conn = self._connection()
        async with conn.execute(
            """
            SELECT *
            FROM matches
            WHERE status IN ('locked', 'finished')
            ORDER BY kickoff_time DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def list_upcoming_matches(self, *, days: int, limit: int = 20) -> list[dict[str, Any]]:
        conn = self._connection()
        async with conn.execute(
            """
            SELECT *
            FROM matches
            WHERE status = ?
            ORDER BY kickoff_time ASC, id ASC
            """,
            (SCHEDULED,),
        ) as cursor:
            rows = [dict(row) for row in await cursor.fetchall()]

        now = now_in_tz(self.tz)
        horizon = now + timedelta(days=days)
        filtered = [
            row
            for row in rows
            if now <= parse_datetime(row["kickoff_time"], self.tz) <= horizon
        ]
        filtered.sort(key=lambda row: (parse_datetime(row["kickoff_time"], self.tz), row["id"]))
        return filtered[:limit]

    async def list_future_matches_with_predictions(
        self,
        telegram_id: int,
        *,
        days: int = 90,
    ) -> list[dict[str, Any]]:
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            return []

        conn = self._connection()
        async with conn.execute(
            """
            SELECT
                m.*,
                p.prediction AS user_prediction
            FROM matches m
            LEFT JOIN predictions p
                ON p.match_id = m.id AND p.user_id = ?
            WHERE m.status IN ('scheduled', 'locked')
            ORDER BY m.kickoff_time ASC, m.id ASC
            """,
            (user["id"],),
        ) as cursor:
            rows = [dict(row) for row in await cursor.fetchall()]

        now = now_in_tz(self.tz)
        horizon = now + timedelta(days=days)
        filtered = [
            row
            for row in rows
            if now <= parse_datetime(row["kickoff_time"], self.tz) <= horizon
        ]
        filtered.sort(key=lambda row: (parse_datetime(row["kickoff_time"], self.tz), row["id"]))
        return filtered

    async def get_user_prediction(self, telegram_id: int, match_id: int) -> str | None:
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            return None

        conn = self._connection()
        async with conn.execute(
            """
            SELECT prediction
            FROM predictions
            WHERE user_id = ? AND match_id = ?
            """,
            (user["id"], match_id),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return str(row["prediction"])

    async def save_prediction(self, telegram_id: int, match_id: int, prediction: str) -> dict[str, Any]:
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            raise PredictionError("Сначала нужно зарегистрироваться через /start.")

        match = await self.get_match(match_id)
        if match is None:
            raise PredictionError("Матч не найден.")

        if match["match_type"] not in VALID_PREDICTIONS:
            raise PredictionError("У матча указан неизвестный тип.")
        if prediction not in VALID_PREDICTIONS[match["match_type"]]:
            raise PredictionError("Такой прогноз недоступен для этого матча.")

        kickoff_time = parse_datetime(match["kickoff_time"], self.tz)
        now = now_in_tz(self.tz)
        if match["status"] == SCHEDULED and kickoff_time <= now:
            await self._lock_match(match["id"])
            raise PredictionError("Матч уже начался. Прогнозы закрыты.")

        if match["status"] != SCHEDULED:
            raise PredictionError("Прогнозы на этот матч уже закрыты.")

        conn = self._connection()
        timestamp = iso_now(self.tz)
        await conn.execute(
            """
            INSERT INTO predictions (user_id, match_id, prediction, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, match_id) DO UPDATE SET
                prediction = excluded.prediction,
                updated_at = excluded.updated_at
            """,
            (user["id"], match_id, prediction, timestamp, timestamp),
        )
        await conn.commit()

        refreshed = await self.get_match(match_id)
        if refreshed is None:
            raise RuntimeError("Match disappeared after prediction save")
        return refreshed

    async def _lock_match(self, match_id: int) -> None:
        conn = self._connection()
        await conn.execute(
            """
            UPDATE matches
            SET status = ?, updated_at = ?
            WHERE id = ? AND status = ?
            """,
            (LOCKED, iso_now(self.tz), match_id, SCHEDULED),
        )
        await conn.commit()

    async def lock_due_matches(self) -> list[dict[str, Any]]:
        conn = self._connection()
        async with conn.execute(
            "SELECT * FROM matches WHERE status = ? ORDER BY kickoff_time ASC",
            (SCHEDULED,),
        ) as cursor:
            rows = [dict(row) for row in await cursor.fetchall()]

        now = now_in_tz(self.tz)
        due = [row for row in rows if parse_datetime(row["kickoff_time"], self.tz) <= now]
        if not due:
            return []

        timestamp = iso_now(self.tz)
        await conn.executemany(
            """
            UPDATE matches
            SET status = ?, updated_at = ?
            WHERE id = ? AND status = ?
            """,
            [(LOCKED, timestamp, row["id"], SCHEDULED) for row in due],
        )
        await conn.commit()
        return due

    async def score_finished_matches(self) -> list[dict[str, Any]]:
        conn = self._connection()
        async with conn.execute(
            """
            SELECT *
            FROM matches
            WHERE status = ?
                AND score IS NOT NULL
                AND winner IS NOT NULL
            ORDER BY kickoff_time ASC, id ASC
            """,
            (FINISHED,),
        ) as cursor:
            matches = [dict(row) for row in await cursor.fetchall()]

        scored_matches: list[dict[str, Any]] = []
        for match in matches:
            if match["match_type"] == PLAYOFF and match["winner"] == PREDICTION_DRAW:
                continue

            async with conn.execute(
                """
                SELECT user_id, prediction
                FROM predictions
                WHERE match_id = ? AND prediction != ?
                """,
                (match["id"], PREDICTION_NONE),
            ) as cursor:
                predictions = [dict(row) for row in await cursor.fetchall()]

            timestamp = iso_now(self.tz)
            event_rows = []
            for prediction in predictions:
                points = 1 if prediction["prediction"] == match["winner"] else -1
                event_rows.append(
                    (
                        prediction["user_id"],
                        match["id"],
                        prediction["prediction"],
                        match["winner"],
                        points,
                        timestamp,
                    )
                )

            if event_rows:
                await conn.executemany(
                    """
                    INSERT OR IGNORE INTO score_events
                        (user_id, match_id, prediction, result, points, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    event_rows,
                )

            await conn.execute(
                """
                UPDATE matches
                SET status = ?, updated_at = ?
                WHERE id = ? AND status = ?
                """,
                (SCORED, timestamp, match["id"], FINISHED),
            )
            await conn.commit()
            scored_matches.append({"match_id": match["id"], "events": len(event_rows)})

        return scored_matches

    async def update_match_result(self, match_id: int, score: str, winner: str) -> dict[str, Any]:
        match = await self.get_match(match_id)
        if match is None:
            raise MatchResultError("Матч не найден.")
        if match["status"] == SCORED:
            raise MatchResultError("Матч уже обработан, результат через бота изменить нельзя.")
        if match["match_type"] == PLAYOFF and winner == PREDICTION_DRAW:
            raise MatchResultError("Для плей-офф ничья невозможна. Укажите итоговый счёт с победителем.")

        conn = self._connection()
        await conn.execute(
            """
            UPDATE matches
            SET status = ?,
                score = ?,
                winner = ?,
                result_recorded_at = NULL,
                updated_at = ?
            WHERE id = ?
            """,
            (FINISHED, score, winner, iso_now(self.tz), match_id),
        )
        await conn.commit()
        updated = await self.get_match(match_id)
        if updated is None:
            raise RuntimeError("Match disappeared after result update")
        return updated

    async def reset_test_data(self) -> None:
        conn = self._connection()
        await conn.execute("DELETE FROM score_events")
        await conn.execute("DELETE FROM predictions")
        await conn.execute("DELETE FROM users")
        await conn.execute("DELETE FROM settings")
        await conn.execute(
            """
            UPDATE matches
            SET status = ?,
                score = NULL,
                winner = NULL,
                result_recorded_at = NULL,
                updated_at = ?
            """,
            (SCHEDULED, iso_now(self.tz)),
        )
        await conn.commit()

    async def leaderboard(self) -> list[dict[str, Any]]:
        conn = self._connection()
        async with conn.execute(
            """
            WITH score_stats AS (
                SELECT
                    user_id,
                    COALESCE(SUM(points), 0) AS rating,
                    COALESCE(SUM(CASE WHEN points > 0 THEN points ELSE 0 END), 0) AS positive_points,
                    COALESCE(SUM(CASE WHEN points < 0 THEN points ELSE 0 END), 0) AS negative_points
                FROM score_events
                GROUP BY user_id
            ),
            bet_stats AS (
                SELECT user_id, COUNT(*) AS bets_count
                FROM score_events
                GROUP BY user_id
            )
            SELECT
                u.id,
                u.display_name,
                u.registration_date,
                COALESCE(s.rating, 0) AS rating,
                COALESCE(s.positive_points, 0) AS positive_points,
                COALESCE(s.negative_points, 0) AS negative_points,
                COALESCE(b.bets_count, 0) AS bets_count
            FROM users u
            LEFT JOIN score_stats s ON s.user_id = u.id
            LEFT JOIN bet_stats b ON b.user_id = u.id
            ORDER BY rating DESC, bets_count DESC, registration_date ASC, id ASC
            """
        ) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def list_results_since(self, since_iso: str) -> list[dict[str, Any]]:
        conn = self._connection()
        since = parse_datetime(since_iso, self.tz)
        async with conn.execute(
            """
            SELECT *
            FROM matches
            WHERE status IN ('finished', 'scored')
                AND score IS NOT NULL
                AND winner IS NOT NULL
            ORDER BY kickoff_time ASC, id ASC
            """
        ) as cursor:
            rows = [dict(row) for row in await cursor.fetchall()]

        results = []
        for row in rows:
            recorded_raw = row.get("result_recorded_at") or row["updated_at"] or row["kickoff_time"]
            recorded_at = parse_datetime(recorded_raw, self.tz)
            if recorded_at >= since:
                results.append(row)
        return results

    async def get_setting(self, key: str) -> str | None:
        conn = self._connection()
        async with conn.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return str(row["value"])

    async def set_setting(self, key: str, value: str) -> None:
        conn = self._connection()
        timestamp = iso_now(self.tz)
        await conn.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, value, timestamp),
        )
        await conn.commit()

    async def seed_setting_if_missing(self, key: str, value: str) -> None:
        conn = self._connection()
        timestamp = iso_now(self.tz)
        await conn.execute(
            """
            INSERT OR IGNORE INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
            """,
            (key, value, timestamp),
        )
        await conn.commit()
