from __future__ import annotations

from worldcup_bot.constants import (
    PREDICTION_DRAW,
    PREDICTION_NONE,
    PREDICTION_TEAM1,
    PREDICTION_TEAM2,
    SHORT_PREDICTION_LABELS,
)
from worldcup_bot.timeutils import format_moscow_datetime, parse_datetime


REGISTRATION_PROMPT = (
    "Привет!\n\n"
    "Это бот конкурса прогнозов УЭК на матчи Чемпионата мира по футболу 2026.\n\n"
    "Правила простые – я присылаю ближайшие матчи, ты делаешь прогнозы, раз в сутки "
    "в канале @uekworldcup я публикую результаты матчей и рейтинг участников конкурса. "
    "За верный прогноз начисляется 1 балл, за неверный – снимается 1 балл. "
    "В случае пропуска прогноза (участник не успел сделать до начала матча или нажал вариант skip) "
    "баллы не начисляются и не снимаются. Победитель конкурса получит приятный сюрприз.\n\n"
    "Прогнозы делаются на каждый матч отдельно. Чтобы сделать прогноз, нужно нажать на кнопку под матчем "
    "(я буду присылать расписание):\n"
    "- 1 – победа команды 1\n"
    "- X – ничья\n"
    "- 2 – победа команды 2\n"
    "- skip – не делать прогноз\n\n"
    "Пожалуйста, укажи своё имя или ник для отображения в рейтинге."
)

COMPACT_PREDICTION_LABELS = {
    PREDICTION_TEAM1: "победа 1",
    PREDICTION_TEAM2: "победа 2",
    PREDICTION_DRAW: "ничья",
    PREDICTION_NONE: "без прогноза",
}

MONTH_NAMES = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


def prediction_label(prediction: str | None, match: dict | None = None) -> str:
    if prediction is None:
        return "Не сделан"
    if match is not None:
        if prediction == PREDICTION_TEAM1:
            return f"Победа: {match['team1']}"
        if prediction == PREDICTION_TEAM2:
            return f"Победа: {match['team2']}"
    if prediction == PREDICTION_DRAW:
        return "Ничья"
    if prediction == PREDICTION_NONE:
        return "Не делать прогноз"
    return SHORT_PREDICTION_LABELS.get(prediction, prediction)


def compact_prediction_label(prediction: str | None) -> str:
    if prediction is None:
        return "не выбран"
    return COMPACT_PREDICTION_LABELS.get(prediction, "не выбран")


def format_compact_match_datetime(value: str, tz) -> str:
    dt = parse_datetime(value, tz)
    return f"{dt.day} {MONTH_NAMES[dt.month]}, {dt:%H:%M}"


def format_match_card(match: dict, tz, user_prediction: str | None = None) -> str:
    return f"{format_compact_match_datetime(match['kickoff_time'], tz)} | {match['team1']} – {match['team2']}"


def format_my_predictions(rows: list[dict], tz=None) -> str:
    if not rows:
        return "Будущих матчей пока нет."

    display_rows = rows[:50]
    lines = ["Мои прогнозы:"]
    if len(rows) > 50:
        lines.append("Показаны ближайшие 50 матчей.")
    for row in display_rows:
        label = compact_prediction_label(row.get("user_prediction"))
        lines.append(f"{row['team1']} – {row['team2']} – {label}")
    return "\n".join(lines)


def format_leaderboard(rows: list[dict]) -> str:
    if not rows:
        return "В рейтинге пока нет участников."

    lines = ["Рейтинг участников:"]
    for index, row in enumerate(rows, start=1):
        lines.append(
            (
                f"{index}. {row['display_name']} — {row['rating']} "
                f"(+{row['positive_points']} / {row['negative_points']})"
            )
        )
    return "\n".join(lines)


def format_result_line(match: dict) -> str:
    return f"- {match['team1']} {match['score']} {match['team2']}"


def format_admin_match_option(match: dict, tz) -> str:
    score = match.get("score") or "не внесен"
    return "\n".join(
        [
            f"#{match['id']} {match['team1']} — {match['team2']}",
            f"Начало: {format_moscow_datetime(match['kickoff_time'], tz)} МСК",
            f"Статус: {match['status']}",
            f"Счет: {score}",
        ]
    )


def format_channel_summary(results: list[dict], leaderboard: list[dict]) -> str:
    lines = ["Ежедневная сводка"]

    lines.append("")
    lines.append("Результаты завершенных матчей:")
    if results:
        lines.extend(format_result_line(match) for match in results)
    else:
        lines.append("Новых завершенных матчей нет.")

    lines.append("")
    lines.append("Рейтинг участников:")
    if leaderboard:
        for row in leaderboard:
            lines.append(
                (
                    f"{row['display_name']} — {row['rating']} "
                    f"(+{row['positive_points']} / {row['negative_points']})"
                )
            )
    else:
        lines.append("Участников пока нет.")

    return "\n".join(lines)
