# Отчет по реализации

## 1. Краткое описание архитектуры

Проект реализован как самостоятельный aiogram 3.x бот на Python 3.12+.

- `bot.py` запускает Telegram polling, подключает SQLite и APScheduler.
- `worldcup_bot/config.py` читает `.env` через `python-dotenv`.
- `worldcup_bot/db.py` содержит SQLite-схему, запросы, регистрацию, прогнозы, блокировку матчей, начисление очков и рейтинг.
- `worldcup_bot/handlers.py` содержит пользовательские сценарии `/start`, меню, просмотр матчей, прогнозы, личные прогнозы и рейтинг.
- `worldcup_bot/keyboards.py` строит ReplyKeyboardMarkup главного меню и InlineKeyboardMarkup прогнозов.
- `worldcup_bot/scheduler.py` запускает фоновые задачи: блокировку, скоринг, ежедневную рассылку и публикацию в канал.
- `worldcup_bot/messages.py` форматирует тексты для пользователей и канала.
- `init_db.py` создает/обновляет структуру SQLite.

Фоновые операции используют таймзону из `TIMEZONE`, по умолчанию `Europe/Moscow`.

## 2. Схема БД

### users

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `telegram_id INTEGER NOT NULL UNIQUE`
- `display_name TEXT NOT NULL`
- `registration_date TEXT NOT NULL`

### matches

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `team1 TEXT NOT NULL`
- `team2 TEXT NOT NULL`
- `stage TEXT NOT NULL`
- `match_type TEXT NOT NULL CHECK ('group', 'playoff')`
- `kickoff_time TEXT NOT NULL`
- `status TEXT NOT NULL CHECK ('scheduled', 'locked', 'finished', 'scored')`
- `score TEXT`
- `winner TEXT CHECK ('team1', 'draw', 'team2')`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`
- `result_recorded_at TEXT`

Для `playoff` запрещен `winner = 'draw'`.

### predictions

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `user_id INTEGER NOT NULL REFERENCES users(id)`
- `match_id INTEGER NOT NULL REFERENCES matches(id)`
- `prediction TEXT NOT NULL CHECK ('team1', 'draw', 'team2', 'none')`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`
- `UNIQUE(user_id, match_id)`

### score_events

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `user_id INTEGER NOT NULL REFERENCES users(id)`
- `match_id INTEGER NOT NULL REFERENCES matches(id)`
- `prediction TEXT NOT NULL`
- `result TEXT NOT NULL`
- `points INTEGER NOT NULL CHECK (-1, 1)`
- `created_at TEXT NOT NULL`
- `UNIQUE(user_id, match_id)`

### settings

- `key TEXT PRIMARY KEY`
- `value TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

## 3. Список созданных файлов

- `.env.example`
- `.gitignore`
- `DB.md`
- `INSTALL.md`
- `README.md`
- `bot.py`
- `chatgpt_report.md`
- `init_db.py`
- `requirements.txt`
- `samples/matches.sql`
- `worldcup_bot/__init__.py`
- `worldcup_bot/config.py`
- `worldcup_bot/constants.py`
- `worldcup_bot/db.py`
- `worldcup_bot/handlers.py`
- `worldcup_bot/keyboards.py`
- `worldcup_bot/messages.py`
- `worldcup_bot/scheduler.py`
- `worldcup_bot/timeutils.py`

## 4. Пример заполнения расписания матчей

```sql
INSERT INTO matches (team1, team2, stage, match_type, kickoff_time, status)
VALUES
    ('Аргентина', 'Франция', 'Групповой этап', 'group', '2026-06-14T21:00:00+03:00', 'scheduled'),
    ('Германия', 'Испания', 'Групповой этап', 'group', '2026-06-15T18:00:00+03:00', 'scheduled'),
    ('Бразилия', 'Нидерланды', '1/8 финала', 'playoff', '2026-06-29T21:00:00+03:00', 'scheduled');
```

Пример внесения результата:

```sql
UPDATE matches
SET status = 'finished',
    score = '2:1',
    winner = 'team1'
WHERE id = 1;
```

## 5. Инструкция запуска

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python init_db.py
python bot.py
```

Минимальные переменные `.env`:

```env
BOT_TOKEN=123456789:telegram_bot_token
CHANNEL_ID=@your_channel_username
TIMEZONE=Europe/Moscow
```

## 6. Результат git status --short

```text
?? .env.example
?? .gitignore
?? DB.md
?? INSTALL.md
?? README.md
?? bot.py
?? chatgpt_report.md
?? init_db.py
?? requirements.txt
?? samples/
?? worldcup_bot/
```

## 7. Известные ограничения и технический долг

- Администрирование матчей намеренно выполняется напрямую в SQLite, без Telegram-интерфейса администратора.
- Ежедневная сводка канала использует `settings.last_channel_summary_at`; если вручную сильно менять старые результаты после публикации, может понадобиться сбросить этот ключ.
- Личные состояния регистрации хранятся в `MemoryStorage`, поэтому незавершенный ввод имени сбросится при рестарте бота.
- Нет отдельного test suite; выполнены smoke-проверки компиляции, импорта Telegram-слоя и сценария начисления очков на временной SQLite-базе.
