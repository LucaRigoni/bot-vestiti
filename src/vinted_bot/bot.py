from __future__ import annotations

import logging
from dataclasses import dataclass

from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .config import BRANDS, CATEGORY_OPTIONS, GENDERS, Settings
from .models import UserPreference
from .storage import PreferenceStore
from .vinted_client import VintedClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHOOSING_BRAND, CHOOSING_GENDER, CHOOSING_CATEGORY, CHOOSING_MAX_PRICE = range(4)


@dataclass
class BotRuntime:
    settings: Settings
    store: PreferenceStore
    client: VintedClient
    preferences: dict[int, UserPreference]


def _keyboard_from_options(options: list[str]) -> list[list[KeyboardButton]]:
    return [[KeyboardButton(option)] for option in options]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    keyboard = _keyboard_from_options(BRANDS)
    await update.message.reply_text(
        "Ciao! Ti aiuto a trovare articoli per il reselling.\n"
        "Setup filtri (1/4): scegli la marca che vuoi monitorare:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return CHOOSING_BRAND


async def select_brand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    runtime: BotRuntime = context.application.bot_data["runtime"]
    brand = (update.message.text or "").strip()
    if brand not in BRANDS:
        await update.message.reply_text("Seleziona una marca dalla tastiera proposta.")
        return CHOOSING_BRAND

    catalog_options = await runtime.client.get_catalog_options()
    if not catalog_options:
        catalog_options = CATEGORY_OPTIONS

    genders = sorted([g for g in catalog_options.keys() if g in GENDERS], key=GENDERS.index)
    if not genders:
        genders = GENDERS

    context.user_data["brand"] = brand
    context.user_data["catalog_options"] = catalog_options
    keyboard = _keyboard_from_options(genders)
    await update.message.reply_text(
        f"Perfetto, marca: {brand}. Setup filtri (2/4): scegli il genere:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return CHOOSING_GENDER


async def select_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    gender = (update.message.text or "").strip()
    catalog_options = context.user_data.get("catalog_options", CATEGORY_OPTIONS)
    available_genders = [g for g in catalog_options.keys() if g in GENDERS] or GENDERS

    if gender not in available_genders:
        await update.message.reply_text("Seleziona Uomo o Donna dalla tastiera.")
        return CHOOSING_GENDER

    categories = catalog_options.get(gender) or CATEGORY_OPTIONS.get(gender, [])
    context.user_data["gender"] = gender
    context.user_data["categories"] = categories
    keyboard = _keyboard_from_options(categories)
    await update.message.reply_text(
        f"Genere: {gender}. Setup filtri (3/4): scegli la tipologia di capo:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return CHOOSING_CATEGORY


async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    category = (update.message.text or "").strip()
    valid_categories = context.user_data.get("categories", [])
    if category not in valid_categories:
        await update.message.reply_text("Scegli una categoria tra quelle proposte dalla tastiera.")
        return CHOOSING_CATEGORY

    context.user_data["category"] = category
    await update.message.reply_text(
        f"Perfetto, capo: {category}. Setup filtri (4/4): inserisci il prezzo massimo in euro (es. 30).",
        reply_markup=ReplyKeyboardRemove(),
    )
    return CHOOSING_MAX_PRICE


async def select_max_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    runtime: BotRuntime = context.application.bot_data["runtime"]
    text = (update.message.text or "").strip().replace(",", ".")
    try:
        max_price = float(text)
        if max_price <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Prezzo non valido. Inserisci un numero positivo, es. 10")
        return CHOOSING_MAX_PRICE

    brand = context.user_data["brand"]
    gender = context.user_data["gender"]
    category = context.user_data["category"]
    chat_id = update.effective_chat.id

    runtime.preferences[chat_id] = UserPreference(
        chat_id=chat_id,
        brand=brand,
        gender=gender,
        category=category,
        max_price=max_price,
    )
    runtime.store.save(runtime.preferences)

    await update.message.reply_text(
        "Configurazione salvata ✅\n"
        f"Marca: {brand}\n"
        f"Genere: {gender}\n"
        f"Categoria: {category}\n"
        f"Prezzo massimo: €{max_price:.2f}\n"
        "Da ora ti avviso quando trovo nuovi articoli dal più recente."
    )
    return ConversationHandler.END


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime: BotRuntime = context.application.bot_data["runtime"]
    chat_id = update.effective_chat.id
    pref = runtime.preferences.get(chat_id)
    if not pref:
        await update.message.reply_text("Non hai ancora una configurazione. Usa /start")
        return

    await update.message.reply_text(
        "Monitoraggio attivo:\n"
        f"Marca: {pref.brand}\n"
        f"Genere: {pref.gender}\n"
        f"Categoria: {pref.category}\n"
        f"Prezzo massimo: €{pref.max_price:.2f}"
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime: BotRuntime = context.application.bot_data["runtime"]
    chat_id = update.effective_chat.id
    removed = runtime.preferences.pop(chat_id, None)
    runtime.store.save(runtime.preferences)
    if removed:
        await update.message.reply_text("Monitoraggio disattivato. Puoi rifare setup con /start")
    else:
        await update.message.reply_text("Non avevi un monitoraggio attivo.")


async def monitor_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime: BotRuntime = context.application.bot_data["runtime"]

    for chat_id, pref in runtime.preferences.items():
        try:
            items = await runtime.client.search_items(
                brand=pref.brand,
                gender=pref.gender,
                category=pref.category,
                max_price=pref.max_price,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Errore ricerca Vinted per %s: %s", chat_id, exc)
            continue

        fresh_items = [item for item in items if item.item_id not in pref.seen_item_ids]
        if not pref.seen_item_ids:
            for item in items:
                pref.seen_item_ids.add(item.item_id)
            continue

        for item in reversed(fresh_items):
            pref.seen_item_ids.add(item.item_id)
            caption = (
                "🆕 Nuovo articolo trovato!\n"
                f"{item.title}\n"
                f"Prezzo: €{item.price_eur:.2f}\n"
                f"Filtro: {pref.brand} | {pref.gender} | {pref.category}\n"
                f"{item.url}"
            )
            if item.image_url:
                await context.bot.send_photo(chat_id=chat_id, photo=item.image_url, caption=caption)
            else:
                await context.bot.send_message(chat_id=chat_id, text=caption)

        pref.seen_item_ids = set(sorted(pref.seen_item_ids)[-500:])

    runtime.store.save(runtime.preferences)


def build_application(runtime: BotRuntime) -> Application:
    app = Application.builder().token(runtime.settings.telegram_token).build()
    app.bot_data["runtime"] = runtime

    conversation = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_BRAND: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_brand)],
            CHOOSING_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_gender)],
            CHOOSING_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_category)],
            CHOOSING_MAX_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_max_price)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conversation)
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("stop", stop))

    app.job_queue.run_repeating(
        monitor_job,
        interval=runtime.settings.polling_interval_seconds,
        first=5,
        name="vinted-monitor",
    )
    return app
