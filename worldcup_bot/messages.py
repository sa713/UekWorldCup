from __future__ import annotations

from worldcup_bot.constants import (
    PREDICTION_DRAW,
    PREDICTION_NONE,
    PREDICTION_TEAM1,
    PREDICTION_TEAM2,
    SHORT_PREDICTION_LABELS,
)
from worldcup_bot.timeutils import format_moscow_datetime


COMPACT_PREDICTION_LABELS = {
    PREDICTION_TEAM1: "победа 1",
    PREDICTION_TEAM2: "победа 2",
    PREDICTION_DRAW: "ничья",
    PREDICTION_NONE: "без прогноза",
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


def format_match_card(match: dict, tz, user_prediction: str | None = None) -> str:
    lines = [
        f"{match['team1']} — {match['team2']}",
        f"Стадия: {match['stage']}",
    ]
    if match.get("match_type") == "group" and match.get("group_name"):
        lines.append(f"Группа: {match['group_name']}")
    lines.append(f"Начало: {format_moscow_datetime(match['kickoff_time'], tz)} МСК")
    if user_prediction is not None:
        lines.append(f"Ваш прогноз: {prediction_label(user_prediction, match)}")
    return "\n".join(lines)


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
                f"{index}. {row['display_name']} — рейтинг {row['rating']} "
                f"(+{row['positive_points']} / {row['negative_points']}) — "
                f"{row['bets_count']} ставок"
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
                    f"{row['display_name']} — рейтинг {row['rating']} "
                    f"(+{row['positive_points']} / {row['negative_points']}) — "
                    f"{row['bets_count']} ставок"
                )
            )
    else:
        lines.append("Участников пока нет.")

    return "\n".join(lines)
