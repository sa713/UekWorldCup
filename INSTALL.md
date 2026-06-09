# Установка и запуск

## 1. Подготовьте Python

Нужен Python 3.12 или новее.

```bash
python3.12 --version
python3.12 -m venv .venv
source .venv/bin/activate
```

## 2. Установите зависимости

```bash
pip install -r requirements.txt
```

## 3. Создайте `.env`

```bash
cp .env.example .env
```

Заполните значения:

```env
BOT_TOKEN=123456789:telegram_bot_token
CHANNEL_ID=@your_channel_username
ADMIN_USERNAME=example_username
TIMEZONE=Europe/Moscow
DATABASE_PATH=data/worldcup.sqlite3
```

`CHANNEL_ID` может быть username канала (`@channel_name`) или числовой id вида `-100...`. Бот должен быть добавлен в канал с правом публикации сообщений.
`ADMIN_USERNAME` указывается без `@` и включает временные тестовые админ-кнопки только для этого Telegram username.

## 4. Инициализируйте базу

```bash
python init_db.py
```

По умолчанию база создается в `data/worldcup.sqlite3`.

## 5. Добавьте матчи

Можно выполнить пример:

```bash
sqlite3 data/worldcup.sqlite3 < samples/matches.sql
```

Или вручную:

```bash
sqlite3 data/worldcup.sqlite3
```

```sql
INSERT INTO matches (team1, team2, stage, group_name, match_type, kickoff_time, status)
VALUES ('Германия', 'Испания', 'Групповой этап', 'A', 'group', '2026-06-15T18:00:00+03:00', 'scheduled');
```

## 6. Запустите бота

```bash
python bot.py
```

## 7. Внесение результата

После окончания матча обновите запись:

```sql
UPDATE matches
SET status = 'finished',
    score = '0:0',
    winner = 'draw'
WHERE id = 2;
```

Для плей-офф `winner` должен быть `team1` или `team2`.

## Временные админ-кнопки

Если задан `ADMIN_USERNAME`, администратор увидит в главном меню дополнительные temporary/test actions:

- `Админ: внести результат`;
- `Админ: посчитать и опубликовать рейтинг`;
- `Админ: очистить БД`.

Кнопка очистки удаляет только тестовые данные конкурса: `users`, `predictions`, `score_events`, `settings`. Расписание в `matches` сохраняется, а статусы матчей и результаты сбрасываются к тестовому начальному состоянию.

Эти функции предназначены для тестового запуска и позже могут быть удалены.

## Фоновые задачи

Бот запускает APScheduler вместе с polling:

- каждые `LOCK_INTERVAL_MINUTES` минут закрывает прогнозы начавшихся матчей;
- каждые `SCORING_INTERVAL_MINUTES` минут начисляет очки для матчей в статусе `finished`;
- ежедневно в `DAILY_USERS_HOUR:DAILY_USERS_MINUTE` отправляет ближайшие матчи участникам;
- ежедневно в `DAILY_CHANNEL_HOUR:DAILY_CHANNEL_MINUTE` публикует сводку в канал.

Все операции выполняются в таймзоне из `TIMEZONE`, по умолчанию `Europe/Moscow`.
