# Telegram-бот прогнозов на Чемпионат мира

Самостоятельный Telegram-бот для дружеского конкурса прогнозов на футбольные матчи. Денежных ставок, платежей и азартных механик нет: участники выбирают исходы матчей и получают игровые баллы.

## Возможности

- регистрация участника через `/start`;
- главное меню в личном чате: `Ближайшие матчи`, `Мои прогнозы`, `Рейтинг`;
- inline-кнопки прогнозов под каждым матчем;
- один прогноз на матч с неограниченным изменением до начала;
- автоматическая блокировка прогнозов после kickoff;
- автоматическое начисление `+1` за верный прогноз и `-1` за неверный;
- рейтинг с сортировкой по очкам, количеству сделанных прогнозов и дате регистрации;
- ежедневная рассылка ближайших матчей всем участникам;
- ежедневная публикация результатов и рейтинга в канал;
- ручное администрирование расписания и результатов напрямую в SQLite.

## Стек

- Python 3.12+
- aiogram 3.x
- SQLite
- APScheduler
- python-dotenv

## Структура проекта

```text
.
├── bot.py
├── init_db.py
├── requirements.txt
├── .env.example
├── data/
│   └── worldcup.sqlite3
├── scripts/
│   └── smoke_test.py
├── tests/
│   ├── test_leaderboard.py
│   ├── test_predictions.py
│   └── test_scoring.py
├── worldcup_bot/
│   ├── config.py
│   ├── constants.py
│   ├── db.py
│   ├── handlers.py
│   ├── keyboards.py
│   ├── messages.py
│   ├── scheduler.py
│   └── timeutils.py
├── samples/
│   └── matches.sql
├── README.md
├── INSTALL.md
└── DB.md
```

## Быстрый старт

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python init_db.py
python bot.py
```

Перед запуском заполните в `.env` минимум `BOT_TOKEN`, `CHANNEL_ID` и `TIMEZONE`.

## Локальная проверка без Telegram

Smoke-test и pytest-проверки работают только с временной SQLite-базой. Они не требуют Telegram-токена, не читают `.env` и не отправляют сообщения.

```bash
python scripts/smoke_test.py
pytest
```

Smoke-test создает временную базу, добавляет пользователей, групповой матч и матч плей-офф, записывает прогнозы, вносит результаты, запускает начисление очков и печатает итоговый рейтинг.

## Как внести матч

```sql
INSERT INTO matches (team1, team2, stage, group_name, match_type, kickoff_time, status)
VALUES ('Аргентина', 'Франция', 'Групповой этап', 'A', 'group', '2026-06-14T21:00:00+03:00', 'scheduled');
```

`match_type`:

- `group` — доступны победа команды 1, ничья, победа команды 2;
- `playoff` — доступны только победа команды 1 или победа команды 2.

Для группового этапа в `group_name` хранится группа матча из расписания. Для плей-офф это поле остается пустым или `NULL`.

## Как внести результат

```sql
UPDATE matches
SET status = 'finished',
    score = '2:1',
    winner = 'team1'
WHERE id = 1;
```

Планировщик сам переведет матч из `finished` в `scored` и создаст записи в `score_events`.
