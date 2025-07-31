import logging
import os

from core.settings import settings
from services.book_preview import get_pdf_preview_in_memory
from services.errors import send_error_message
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ContextTypes,
)

logger = logging.getLogger("bot")


async def list_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        files = os.listdir(settings.BOOKS_DIR)
        books = [f for f in files if f.lower().endswith(".pdf")]

        if not books:
            await send_error_message(update, "В библиотеке нет доступных книг.")
            return

        for book in books:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=get_pdf_preview_in_memory(book),
                caption=f"Забрать книгу: {book}",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("Забрать", callback_data=f"get_book:{book}")]]
                ),
            )

        if update.message:
            await update.message.reply_text("Выберите книгу:")
        elif update.callback_query:
            await update.callback_query.message.edit_text("Выберите книгу:")

    except Exception as e:
        error = f"Ошибка при чтении каталога книг: {e}"
        logger.error(error)
        await send_error_message(update, error)
