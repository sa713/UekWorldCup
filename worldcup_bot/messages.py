from __future__ import annotations

from worldcup_bot.constants import (
    PREDICTION_DRAW,
    PREDICTION_NONE,
    PREDICTION_TEAM1,
    PREDICTION_TEAM2,
    SHORT_PREDICTION_LABELS,
)
from worldcup_bot.timeutils import format_moscow_datetime


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


def format_match_card(match: dict, tz, user_prediction: str | None = None) -> str:
    lines = [
        f"{match['team1']} — {match['team2']}",
        f"Стадия: {match['stage']}",
        f"Начало: {format_moscow_datetime(match['kickoff_time'], tz)} МСК",
    ]
    if user_prediction is not None:
        lines.append(f"Ваш прогноз: {prediction_label(user_prediction, match)}")
    return "\n".join(lines)


def format_my_predictions(rows: list[dict], tz) -> str:
    if not rows:
        return "Будущих матчей пока нет."

    lines = ["Ваши прогнозы на будущие матчи:"]
    for row in rows:
        label = prediction_label(row.get("user_prediction"), row)
        lines.append(
            "\n".join(
                [
                    "",
                    f"{format_moscow_datetime(row['kickoff_time'], tz)} МСК",
                    f"{row['team1']} — {row['team2']}",
                    f"Стадия: {row['stage']}",
                    f"Прогноз: {label}",
                ]
            )
        )
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
