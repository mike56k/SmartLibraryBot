import logging
import os

from core.settings import settings
from services.errors import send_error_message
from telegram import Update
from telegram.ext import (
    ContextTypes,
)

logger = logging.getLogger("bot")


async def get_book(update: Update, context: ContextTypes.DEFAULT_TYPE, book_name: str):
    user_id = update.effective_user.id
    query = update.callback_query
    # Удаляем сообщение со списком книг после нажатия кнопки
    try:
        await query.message.delete()
    except Exception as e:
        error = f"Не удалось удалить сообщение: {e}"
        logger.error(error)
        await send_error_message(update, error)

    if settings.PUNISHMENT_SYSTEM_SERVICE.get_user_info(user_id):
        await send_error_message(update, "Сначала верните текущую книгу, которую взяли.")
        return

    filepath = os.path.join(settings.BOOKS_DIR, book_name)
    if not os.path.isfile(filepath):
        await send_error_message(update, "Такой книги нет или она недоступна.")
        return

    # Отправляем файл книги и фиксируем выдачу
    try:
        with open(filepath, "rb") as file:
            await query.message.reply_document(document=file, filename=book_name)
    except Exception as e:
        error = f"Ошибка при отправке книги: {e}"
        logger.error(error)
        await send_error_message(update, error)
        return

    # Удаляем файл из каталога и отмечаем книгу как выданную
    try:
        os.remove(filepath)
        settings.PUNISHMENT_SYSTEM_SERVICE.add_borrow(user_id, book_name)
    except Exception as e:
        error = f"Ошибка при обновлении статуса книги: {e}"
        logger.error(error)
        await send_error_message(update, error)
        return

    await query.message.reply_text(f"Вы взяли книгу '{book_name}'. Пожалуйста, верните её позже!")


async def return_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info = settings.PUNISHMENT_SYSTEM_SERVICE.get_user_info(user_id)
    if not user_info:
        await send_error_message(update, "У вас нет взятых книг для возврата.")
        return

    document = update.message.document
    if not document or not document.file_name.lower().endswith(".pdf"):
        await send_error_message(update, "Пожалуйста, загрузите PDF файл с книгой для возврата.")
        return

    book_name = user_info["book"]

    if book_name != document.file_name:
        await send_error_message(update, "Пожалуйста, верните ту же книгу, которую вы взяли!")
        return

    file_path = os.path.join(settings.BOOKS_DIR, book_name)

    try:
        pdf_file = await document.get_file()
        await pdf_file.download_to_drive(file_path)
    except Exception as e:
        error = f"Ошибка при сохранении файла: {e}"
        logger.error(error)
        await send_error_message(update, error)
        return

    settings.PUNISHMENT_SYSTEM_SERVICE.return_book(user_id)

    await update.message.reply_text(f"Спасибо, книга '{book_name}' успешно возвращена в библиотеку!")
