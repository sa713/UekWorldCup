from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio

from worldcup_bot.db import Database


@pytest_asyncio.fixture
async def db(tmp_path) -> AsyncIterator[Database]:
    database = Database(tmp_path / "worldcup_test.sqlite3", "Europe/Moscow")
    await database.connect()
    await database.init_schema()
    try:
        yield database
    finally:
        await database.close()
