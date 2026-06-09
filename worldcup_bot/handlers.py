from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from worldcup_bot.config import Config
from worldcup_bot.constants import (
    MAIN_MENU_MY_PREDICTIONS,
    MAIN_MENU_RATING,
    MAIN_MENU_UPCOMING,
)
from worldcup_bot.db import Database, PredictionError
from worldcup_bot.keyboards import main_menu_keyboard, prediction_keyboard
from worldcup_bot.messages import (
    format_leaderboard,
    format_match_card,
    format_my_predictions,
)


class Registration(StatesGroup):
    waiting_for_name = State()


router = Router()


async def _ensure_registered(message: Message, db: Database) -> dict | None:
    user = await db.get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала зарегистрируйтесь: отправьте /start.")
        return None
    return user


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: Database) -> None:
    user = await db.get_user_by_telegram_id(message.from_user.id)
    if user is not None:
        await state.clear()
        await message.answer(
            f"Вы уже зарегистрированы как {user['display_name']}.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await state.set_state(Registration.waiting_for_name)
    await message.answer("Привет! Напишите имя участника для рейтинга.")


@router.message(Command("menu"))
async def cmd_menu(message: Message, db: Database) -> None:
    if await _ensure_registered(message, db) is None:
        return
    await message.answer("Главное меню:", reply_markup=main_menu_keyboard())


@router.message(Registration.waiting_for_name)
async def process_registration_name(message: Message, state: FSMContext, db: Database) -> None:
    display_name = (message.text or "").strip()
    if len(display_name) < 2:
        await message.answer("Имя слишком короткое. Напишите имя участника.")
        return
    if len(display_name) > 80:
        await message.answer("Имя слишком длинное. Используйте до 80 символов.")
        return

    await db.register_user(message.from_user.id, display_name)
    await state.clear()
    await message.answer(
        f"Готово, {display_name}! Теперь можно делать прогнозы.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == MAIN_MENU_UPCOMING)
async def show_upcoming_matches(message: Message, db: Database, config: Config) -> None:
    if await _ensure_registered(message, db) is None:
        return

    matches = await db.list_upcoming_matches(days=config.upcoming_days, limit=20)
    if not matches:
        await message.answer("Ближайших матчей с открытыми прогнозами пока нет.")
        return

    await message.answer("Ближайшие матчи:")
    for match in matches:
        selected = await db.get_user_prediction(message.from_user.id, match["id"])
        await message.answer(
            format_match_card(match, db.tz, selected),
            reply_markup=prediction_keyboard(match, selected),
        )


@router.message(F.text == MAIN_MENU_MY_PREDICTIONS)
async def show_my_predictions(message: Message, db: Database) -> None:
    if await _ensure_registered(message, db) is None:
        return

    rows = await db.list_future_matches_with_predictions(message.from_user.id)
    await message.answer(format_my_predictions(rows, db.tz))


@router.message(F.text == MAIN_MENU_RATING)
async def show_rating(message: Message, db: Database) -> None:
    if await _ensure_registered(message, db) is None:
        return

    await message.answer(format_leaderboard(await db.leaderboard()))


@router.callback_query(F.data.startswith("pred:"))
async def save_prediction(callback: CallbackQuery, db: Database) -> None:
    if callback.from_user is None:
        await callback.answer("Не удалось определить пользователя.", show_alert=True)
        return

    try:
        _, match_id_raw, prediction = callback.data.split(":", 2)
        match_id = int(match_id_raw)
    except (AttributeError, ValueError):
        await callback.answer("Некорректная кнопка прогноза.", show_alert=True)
        return

    try:
        match = await db.save_prediction(callback.from_user.id, match_id, prediction)
    except PredictionError as error:
        await callback.answer(str(error), show_alert=True)
        return

    selected = await db.get_user_prediction(callback.from_user.id, match_id)
    if callback.message is not None:
        await callback.message.edit_text(
            format_match_card(match, db.tz, selected),
            reply_markup=prediction_keyboard(match, selected),
        )
    await callback.answer("Прогноз сохранен.")


@router.message()
async def fallback(message: Message, db: Database) -> None:
    if await _ensure_registered(message, db) is None:
        return
    await message.answer("Выберите действие в меню.", reply_markup=main_menu_keyboard())


def setup_handlers(dispatcher) -> None:
    dispatcher.include_router(router)
