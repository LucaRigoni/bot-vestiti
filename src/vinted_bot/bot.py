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

from .config import BRANDS, Settings
from .models import UserPreference
from .storage import PreferenceStore
from .vinted_client import VintedClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHOOSING_BRAND, CHOOSING_MAX_PRICE = range(2)


@dataclass
class BotRuntime:
    settings: Settings
    store: PreferenceStore
    client: VintedClient
    preferences: dict[int, UserPreference]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [[KeyboardButton(b)] for b in BRANDS]
    await update.message.reply_text(
        "Ciao! Ti aiuto a trovare articoli per il reselling.\n"
        "Scegli la marca che vuoi monitorare:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return CHOOSING_BRAND


async def select_brand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    brand = (update.message.text or "").strip()
    if brand not in BRANDS:
        await update.message.reply_text("Seleziona una marca dalla tastiera proposta.")
        return CHOOSING_BRAND

    context.user_data["brand"] = brand
    await update.message.reply_text(
        f"Perfetto, marca: {brand}. Ora inserisci il prezzo massimo in euro (es. 80).",
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
        await update.message.reply_text("Prezzo non valido. Inserisci un numero positivo, es. 65.5")
        return CHOOSING_MAX_PRICE

    brand = context.user_data["brand"]
    chat_id = update.effective_chat.id
    runtime.preferences[chat_id] = UserPreference(chat_id=chat_id, brand=brand, max_price=max_price)
    runtime.store.save(runtime.preferences)

    await update.message.reply_text(
        f"Configurazione salvata ✅\nMarca: {brand}\nPrezzo massimo: €{max_price:.2f}\n"
        "Da ora ti avviso quando trovo nuovi articoli."
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
        f"Monitoraggio attivo:\nMarca: {pref.brand}\nPrezzo massimo: €{pref.max_price:.2f}"
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
            items = await runtime.client.search_items(pref.brand, pref.max_price)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Errore ricerca Vinted per %s: %s", chat_id, exc)
            continue

        fresh_items = [item for item in items if item.item_id not in pref.seen_item_ids]
        if not pref.seen_item_ids:
            # prima sincronizzazione: evita spam storico
            for item in items:
                pref.seen_item_ids.add(item.item_id)
            continue

        for item in reversed(fresh_items):
            pref.seen_item_ids.add(item.item_id)
            text = (
                "🆕 Nuovo articolo trovato!\n"
                f"*{item.title}*\n"
                f"Prezzo: €{item.price_eur:.2f}\n"
                f"Marca monitorata: {pref.brand}\n"
                f"{item.url}"
            )
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")

        pref.seen_item_ids = set(sorted(pref.seen_item_ids)[-500:])

    runtime.store.save(runtime.preferences)


def build_application(runtime: BotRuntime) -> Application:
    app = Application.builder().token(runtime.settings.telegram_token).build()
    app.bot_data["runtime"] = runtime

    conversation = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_BRAND: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_brand)],
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
