-- Пример ручного заполнения расписания.
-- Если в kickoff_time нет смещения таймзоны, бот считает время московским.

INSERT INTO matches (team1, team2, stage, match_type, kickoff_time, status)
VALUES
    ('Аргентина', 'Франция', 'Групповой этап', 'group', '2026-06-14T21:00:00+03:00', 'scheduled'),
    ('Германия', 'Испания', 'Групповой этап', 'group', '2026-06-15T18:00:00+03:00', 'scheduled'),
    ('Бразилия', 'Нидерланды', '1/8 финала', 'playoff', '2026-06-29T21:00:00+03:00', 'scheduled');

-- Пример внесения результата после матча.
-- Для группового этапа winner может быть team1, draw или team2.
-- Для плей-офф winner может быть только team1 или team2.

UPDATE matches
SET status = 'finished',
    score = '2:1',
    winner = 'team1'
WHERE id = 1;
