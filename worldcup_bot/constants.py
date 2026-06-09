GROUP = "group"
PLAYOFF = "playoff"

SCHEDULED = "scheduled"
LOCKED = "locked"
FINISHED = "finished"
SCORED = "scored"

PREDICTION_TEAM1 = "team1"
PREDICTION_DRAW = "draw"
PREDICTION_TEAM2 = "team2"
PREDICTION_NONE = "none"

PREDICTION_LABELS = {
    PREDICTION_TEAM1: "Победа команды 1",
    PREDICTION_DRAW: "Ничья",
    PREDICTION_TEAM2: "Победа команды 2",
    PREDICTION_NONE: "Не делать прогноз",
}

SHORT_PREDICTION_LABELS = {
    PREDICTION_TEAM1: "П1",
    PREDICTION_DRAW: "Ничья",
    PREDICTION_TEAM2: "П2",
    PREDICTION_NONE: "Без прогноза",
}

VALID_PREDICTIONS = {
    GROUP: {PREDICTION_TEAM1, PREDICTION_DRAW, PREDICTION_TEAM2, PREDICTION_NONE},
    PLAYOFF: {PREDICTION_TEAM1, PREDICTION_TEAM2, PREDICTION_NONE},
}

MAIN_MENU_UPCOMING = "Ближайшие матчи"
MAIN_MENU_MY_PREDICTIONS = "Мои прогнозы"
MAIN_MENU_RATING = "Рейтинг"

# Temporary/test admin actions for local tournament dry runs.
ADMIN_MENU_ENTER_RESULT = "Админ: внести результат"
ADMIN_MENU_PUBLISH_RATING = "Админ: посчитать и опубликовать рейтинг"
ADMIN_MENU_CLEAR_DB = "Админ: очистить БД"
