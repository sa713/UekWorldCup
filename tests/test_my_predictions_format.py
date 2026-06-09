from __future__ import annotations

from worldcup_bot.messages import format_my_predictions


def test_format_my_predictions_uses_compact_lines():
    text = format_my_predictions(
        [
            {"team1": "Мексика", "team2": "ЮАР", "user_prediction": "team1"},
            {"team1": "Бразилия", "team2": "Марокко", "user_prediction": "draw"},
            {"team1": "Германия", "team2": "Испания", "user_prediction": None},
            {"team1": "Португалия", "team2": "Нидерланды", "user_prediction": "team2"},
            {"team1": "Канада", "team2": "Катар", "user_prediction": "none"},
        ]
    )

    assert text == "\n".join(
        [
            "Мои прогнозы:",
            "Мексика – ЮАР – победа 1",
            "Бразилия – Марокко – ничья",
            "Германия – Испания – не выбран",
            "Португалия – Нидерланды – победа 2",
            "Канада – Катар – без прогноза",
        ]
    )


def test_format_my_predictions_limits_long_output_to_50_matches():
    rows = [
        {"team1": f"Команда {index}", "team2": "Соперник", "user_prediction": None}
        for index in range(51)
    ]

    text = format_my_predictions(rows)

    assert "Показаны ближайшие 50 матчей." in text
    assert "Команда 49 – Соперник – не выбран" in text
    assert "Команда 50 – Соперник – не выбран" not in text
