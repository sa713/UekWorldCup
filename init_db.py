from __future__ import annotations

import asyncio

from worldcup_bot.config import load_config
from worldcup_bot.db import Database


async def main() -> None:
    config = load_config(require_bot_token=False)
    db = Database(config.database_path, config.timezone)
    await db.connect()
    await db.init_schema()
    await db.close()
    print(f"Database initialized: {config.database_path}")


if __name__ == "__main__":
    asyncio.run(main())
