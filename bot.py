from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from worldcup_bot.config import load_config
from worldcup_bot.db import Database
from worldcup_bot.handlers import setup_handlers
from worldcup_bot.scheduler import bootstrap_scheduler_settings, create_scheduler


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = load_config()
    db = Database(config.database_path, config.timezone)
    await db.connect()
    await db.init_schema()
    await bootstrap_scheduler_settings(db, config)

    bot = Bot(token=config.bot_token)
    dispatcher = Dispatcher(storage=MemoryStorage())
    setup_handlers(dispatcher)

    scheduler = create_scheduler(bot, db, config)
    scheduler.start()

    try:
        await dispatcher.start_polling(bot, db=db, config=config)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
