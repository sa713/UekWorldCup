from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from worldcup_bot.constants import (
    ADMIN_MENU_CLEAR_DB,
    ADMIN_MENU_ENTER_RESULT,
    ADMIN_MENU_PUBLISH_RATING,
    GROUP,
    MAIN_MENU_MY_PREDICTIONS,
    MAIN_MENU_RATING,
    MAIN_MENU_UPCOMING,
    PREDICTION_DRAW,
    PREDICTION_NONE,
    PREDICTION_TEAM1,
    PREDICTION_TEAM2,
)


def main_menu_keyboard(*, is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=MAIN_MENU_UPCOMING)],
        [
            KeyboardButton(text=MAIN_MENU_MY_PREDICTIONS),
            KeyboardButton(text=MAIN_MENU_RATING),
        ],
    ]
    if is_admin:
        keyboard.extend(
            [
                [KeyboardButton(text=ADMIN_MENU_ENTER_RESULT)],
                [KeyboardButton(text=ADMIN_MENU_PUBLISH_RATING)],
                [KeyboardButton(text=ADMIN_MENU_CLEAR_DB)],
            ]
        )

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def prediction_keyboard(match: dict, selected: str | None = None) -> InlineKeyboardMarkup:
    def label(text: str, value: str) -> str:
        return f"{text} ✓" if selected == value else text

    rows = [
        [
            InlineKeyboardButton(
                text=label(match["team1"], PREDICTION_TEAM1),
                callback_data=f"pred:{match['id']}:{PREDICTION_TEAM1}",
            )
        ],
        [
            InlineKeyboardButton(
                text=label(match["team2"], PREDICTION_TEAM2),
                callback_data=f"pred:{match['id']}:{PREDICTION_TEAM2}",
            )
        ],
    ]

    if match["match_type"] == GROUP:
        rows.insert(
            1,
            [
                InlineKeyboardButton(
                    text=label("Ничья", PREDICTION_DRAW),
                    callback_data=f"pred:{match['id']}:{PREDICTION_DRAW}",
                )
            ],
        )

    rows.append(
        [
            InlineKeyboardButton(
                text=label("Не делать прогноз", PREDICTION_NONE),
                callback_data=f"pred:{match['id']}:{PREDICTION_NONE}",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_matches_keyboard(matches: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"#{match['id']} {match['team1']} — {match['team2']}",
                callback_data=f"admin_result:{match['id']}",
            )
        ]
        for match in matches
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_clear_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да, очистить", callback_data="admin_clear:yes"),
                InlineKeyboardButton(text="Отмена", callback_data="admin_clear:no"),
            ]
        ]
    )
