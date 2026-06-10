from __future__ import annotations

from datetime import timedelta

from aiogram import F, Router
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from worldcup_bot.admin import is_admin_username, normalize_score, winner_from_score
from worldcup_bot.config import Config
from worldcup_bot.constants import (
    ADMIN_MENU_CLEAR_DB,
    ADMIN_MENU_ENTER_RESULT,
    ADMIN_MENU_PUBLISH_RATING,
    MAIN_MENU_MY_PREDICTIONS,
    MAIN_MENU_RATING,
    MAIN_MENU_UPCOMING,
)
from worldcup_bot.db import Database, MatchResultError, PredictionError
from worldcup_bot.keyboards import (
    admin_clear_confirm_keyboard,
    admin_matches_keyboard,
    main_menu_keyboard,
    prediction_keyboard,
)
from worldcup_bot.messages import (
    REGISTRATION_PROMPT,
    format_admin_match_option,
    format_channel_summary,
    format_leaderboard,
    format_match_card,
    format_my_predictions,
)
from worldcup_bot.timeutils import now_in_tz


class Registration(StatesGroup):
    waiting_for_name = State()


class AdminResult(StatesGroup):
    choosing_match = State()
    waiting_for_score = State()


router = Router()


def _is_admin_message(message: Message, config: Config) -> bool:
    return is_admin_username(message.from_user.username if message.from_user else None, config.admin_username)


def _is_admin_callback(callback: CallbackQuery, config: Config) -> bool:
    return is_admin_username(callback.from_user.username if callback.from_user else None, config.admin_username)


async def _deny_admin_message(message: Message) -> None:
    await message.answer("Админ-функции недоступны.")


async def _deny_admin_callback(callback: CallbackQuery) -> None:
    await callback.answer("Админ-функции недоступны.", show_alert=True)


async def _ensure_registered(message: Message, db: Database) -> dict | None:
    user = await db.get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала зарегистрируйтесь: отправьте /start.")
        return None
    return user


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    user = await db.get_user_by_telegram_id(message.from_user.id)
    if user is not None:
        await state.clear()
        await message.answer(
            f"Вы уже зарегистрированы как {user['display_name']}.",
            reply_markup=main_menu_keyboard(is_admin=_is_admin_message(message, config)),
        )
        return

    await state.set_state(Registration.waiting_for_name)
    await message.answer(REGISTRATION_PROMPT)


@router.message(Command("menu"))
async def cmd_menu(message: Message, db: Database, config: Config) -> None:
    if await _ensure_registered(message, db) is None:
        return
    await message.answer(
        "Главное меню:",
        reply_markup=main_menu_keyboard(is_admin=_is_admin_message(message, config)),
    )


@router.message(Registration.waiting_for_name)
async def process_registration_name(message: Message, state: FSMContext, db: Database, config: Config) -> None:
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
        reply_markup=main_menu_keyboard(is_admin=_is_admin_message(message, config)),
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
async def show_my_predictions(message: Message, db: Database, config: Config) -> None:
    if await _ensure_registered(message, db) is None:
        return

    rows = await db.list_future_matches_with_predictions(
        message.from_user.id,
        days=config.upcoming_days,
    )
    await message.answer(format_my_predictions(rows, db.tz))


@router.message(F.text == MAIN_MENU_RATING)
async def show_rating(message: Message, db: Database) -> None:
    if await _ensure_registered(message, db) is None:
        return

    await message.answer(format_leaderboard(await db.leaderboard()))


@router.message(F.text == ADMIN_MENU_ENTER_RESULT)
async def admin_enter_result(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not _is_admin_message(message, config):
        await _deny_admin_message(message)
        return

    matches = await db.list_matches_for_result_entry(limit=20)
    if not matches:
        await state.clear()
        await message.answer("Нет матчей в статусе locked или finished.")
        return

    await state.set_state(AdminResult.choosing_match)
    lines = ["Выберите матч для внесения результата:"]
    for match in matches:
        lines.append("")
        lines.append(format_admin_match_option(match, db.tz))
    await message.answer("\n".join(lines), reply_markup=admin_matches_keyboard(matches))


@router.callback_query(F.data.startswith("admin_result:"))
async def admin_choose_result_match(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    config: Config,
) -> None:
    if not _is_admin_callback(callback, config):
        await _deny_admin_callback(callback)
        return

    try:
        match_id = int(callback.data.split(":", 1)[1])
    except (AttributeError, ValueError):
        await callback.answer("Некорректный матч.", show_alert=True)
        return

    match = await db.get_match(match_id)
    if match is None:
        await callback.answer("Матч не найден.", show_alert=True)
        return
    if match["status"] == "scored":
        await callback.answer("Матч уже обработан, результат через бота изменить нельзя.", show_alert=True)
        return

    await state.set_state(AdminResult.waiting_for_score)
    await state.update_data(match_id=match_id)
    if callback.message is not None:
        await callback.message.answer(
            (
                f"Введите результат матча #{match_id} "
                f"{match['team1']} — {match['team2']} в формате 2:1."
            )
        )
    await callback.answer()


@router.message(AdminResult.waiting_for_score)
async def admin_process_score(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not _is_admin_message(message, config):
        await state.clear()
        await _deny_admin_message(message)
        return

    data = await state.get_data()
    match_id = data.get("match_id")
    if match_id is None:
        await state.clear()
        await message.answer("Матч не выбран. Начните заново.")
        return

    try:
        score = normalize_score(message.text or "")
        winner = winner_from_score(score)
        match = await db.update_match_result(int(match_id), score, winner)
    except ValueError as error:
        await message.answer(str(error))
        return
    except MatchResultError as error:
        await message.answer(str(error))
        return

    await state.clear()
    await message.answer(
        (
            f"Результат сохранен: #{match['id']} "
            f"{match['team1']} {match['score']} {match['team2']}."
        )
    )


@router.message(F.text == ADMIN_MENU_PUBLISH_RATING)
async def admin_score_and_publish(message: Message, bot: Bot, db: Database, config: Config) -> None:
    if not _is_admin_message(message, config):
        await _deny_admin_message(message)
        return
    if config.channel_id is None:
        await message.answer("CHANNEL_ID не настроен. Публикация в канал невозможна.")
        return

    scored = await db.score_finished_matches()
    since = (now_in_tz(db.tz) - timedelta(days=config.results_lookback_days)).isoformat(timespec="seconds")
    results = await db.list_results_since(since)
    text = format_channel_summary(results, await db.leaderboard())

    try:
        await bot.send_message(config.channel_id, text)
    except TelegramAPIError as error:
        await message.answer(f"Не удалось опубликовать сводку в канал: {error}")
        return

    await message.answer(f"Готово. Начислено матчей: {len(scored)}. Сводка опубликована в канал.")


@router.message(F.text == ADMIN_MENU_CLEAR_DB)
async def admin_clear_db(message: Message, config: Config) -> None:
    if not _is_admin_message(message, config):
        await _deny_admin_message(message)
        return

    await message.answer(
        "Точно очистить тестовые данные?",
        reply_markup=admin_clear_confirm_keyboard(),
    )


@router.callback_query(F.data.startswith("admin_clear:"))
async def admin_confirm_clear(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not _is_admin_callback(callback, config):
        await _deny_admin_callback(callback)
        return

    action = callback.data.split(":", 1)[1]
    if action != "yes":
        if callback.message is not None:
            await callback.message.edit_text("Очистка отменена.")
        await callback.answer()
        return

    await db.reset_test_data()
    if callback.message is not None:
        await callback.message.edit_text("Тестовые данные очищены. Расписание матчей сохранено.")
    await callback.answer()


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
async def fallback(message: Message, db: Database, config: Config) -> None:
    if await _ensure_registered(message, db) is None:
        return
    await message.answer(
        "Выберите действие в меню.",
        reply_markup=main_menu_keyboard(is_admin=_is_admin_message(message, config)),
    )


def setup_handlers(dispatcher) -> None:
    dispatcher.include_router(router)
