# Структура базы данных

База данных SQLite создается командой:

```bash
python init_db.py
```

## users

Зарегистрированные участники.

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | INTEGER PK | Внутренний идентификатор |
| `telegram_id` | INTEGER UNIQUE | Telegram id пользователя |
| `display_name` | TEXT | Имя для рейтинга, статистики и публикаций |
| `registration_date` | TEXT | ISO-время регистрации |

## matches

Расписание и результаты матчей.

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | INTEGER PK | Идентификатор матча |
| `team1` | TEXT | Команда 1 |
| `team2` | TEXT | Команда 2 |
| `stage` | TEXT | Стадия турнира |
| `group_name` | TEXT | Группа матча, например `A`; для плей-офф `NULL` |
| `match_type` | TEXT | `group` или `playoff` |
| `kickoff_time` | TEXT | Время начала в ISO-формате |
| `status` | TEXT | `scheduled`, `locked`, `finished`, `scored` |
| `score` | TEXT | Счет, например `2:1` |
| `winner` | TEXT | `team1`, `draw`, `team2` |
| `created_at` | TEXT | Время создания записи |
| `updated_at` | TEXT | Время последнего изменения |
| `result_recorded_at` | TEXT | Время фиксации результата |

Для `playoff` значение `winner = 'draw'` запрещено.

Если `kickoff_time` внесен без смещения таймзоны, бот трактует его как московское время:

```sql
'2026-06-14 21:00:00'
```

Рекомендуемый формат:

```sql
'2026-06-14T21:00:00+03:00'
```

## predictions

Прогнозы участников.

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | INTEGER PK | Идентификатор прогноза |
| `user_id` | INTEGER FK | Ссылка на `users.id` |
| `match_id` | INTEGER FK | Ссылка на `matches.id` |
| `prediction` | TEXT | `team1`, `draw`, `team2`, `none` |
| `created_at` | TEXT | Время первого прогноза |
| `updated_at` | TEXT | Время последнего изменения |

Ограничение `UNIQUE(user_id, match_id)` гарантирует один прогноз на матч. Повторное нажатие inline-кнопки обновляет существующую запись.

`none` означает “не делать прогноз” и не учитывается в количестве ставок и начислении очков.

## score_events

История начисления очков.

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | INTEGER PK | Идентификатор события |
| `user_id` | INTEGER FK | Участник |
| `match_id` | INTEGER FK | Матч |
| `prediction` | TEXT | Прогноз, по которому начислены очки |
| `result` | TEXT | Фактический исход |
| `points` | INTEGER | `1` или `-1` |
| `created_at` | TEXT | Время начисления |

Ограничение `UNIQUE(user_id, match_id)` защищает от повторного начисления по одному матчу.

## settings

Служебные настройки.

| Поле | Тип | Описание |
| --- | --- | --- |
| `key` | TEXT PK | Название настройки |
| `value` | TEXT | Значение |
| `updated_at` | TEXT | Время обновления |

Сейчас используется ключ `last_channel_summary_at`, чтобы ежедневная сводка не публиковала одни и те же результаты повторно.

## Жизненный цикл матча

```text
scheduled -> locked -> finished -> scored
```

- `scheduled`: прогнозы открыты;
- `locked`: матч начался, прогнозы закрыты;
- `finished`: результат внесен вручную, очки еще не начислены;
- `scored`: очки начислены автоматически.

## Примеры

Групповой матч:

```sql
INSERT INTO matches (team1, team2, stage, group_name, match_type, kickoff_time, status)
VALUES ('Аргентина', 'Франция', 'Групповой этап', 'A', 'group', '2026-06-14T21:00:00+03:00', 'scheduled');
```

Плей-офф:

```sql
INSERT INTO matches (team1, team2, stage, match_type, kickoff_time, status)
VALUES ('Бразилия', 'Нидерланды', '1/8 финала', 'playoff', '2026-06-29T21:00:00+03:00', 'scheduled');
```

Результат:

```sql
UPDATE matches
SET status = 'finished',
    score = '2:1',
    winner = 'team1'
WHERE id = 1;
```
