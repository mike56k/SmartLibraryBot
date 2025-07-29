import asyncio
import io
import os
from datetime import datetime

from errors import send_error_message
from help import help_text
from logger_config import logger
from pdf2image import convert_from_path
from punishment_system import PunishmentSystem
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

BOOKS_DIR = "books"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Список книг", callback_data="list_books")],
        [InlineKeyboardButton("Мой долг", callback_data="get_my_debt")],
        [InlineKeyboardButton("Помощь", callback_data="help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Это бот-библиотека.", reply_markup=reply_markup)


async def list_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not os.path.exists(BOOKS_DIR):
            await send_error_message(update, "Папка с книгами не найдена.")
            return

        files = os.listdir(BOOKS_DIR)
        books = [f for f in files if f.lower().endswith(".pdf")]

        if not books:
            await send_error_message(update, "В библиотеке нет доступных книг.")
            return

        def get_pdf_preview_in_memory(pdf_path: str):
            # Получаем первую страницу PDF в виде изображения
            images = convert_from_path(f"{BOOKS_DIR}/{pdf_path}", first_page=1, last_page=1)
            if images:
                img_byte_arr = io.BytesIO()
                images[0].save(img_byte_arr, format="JPEG")
                img_byte_arr.seek(0)  # Перемещаем указатель в начало
                return img_byte_arr
            return None

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


async def get_my_debt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info = punishment_system.get_user_info(user_id)
    if not user_info:
        await send_error_message(update, "У вас нет долгов, пользуйтесь на здоровье :)")
        return
    borrowed_at = datetime.fromisoformat(user_info["borrowed_at"])
    debd_message = (
        f"Ваш текущий долг:\n\n"
        f"Название книги: {user_info['book']}\n"
        f"Дата выдачи: {borrowed_at}\n\n"
        f"Не забудьте вернуть вовремя!"
    )

    await send_error_message(update, debd_message)


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

    if punishment_system.get_user_info(user_id):
        await send_error_message(update, "Сначала верните текущую книгу, которую взяли.")
        return

    filepath = os.path.join(BOOKS_DIR, book_name)
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
        punishment_system.add_borrow(user_id, book_name)
    except Exception as e:
        error = f"Ошибка при обновлении статуса книги: {e}"
        logger.error(error)
        await send_error_message(update, error)
        return

    await query.message.reply_text(f"Вы взяли книгу '{book_name}'. Пожалуйста, верните её позже!")


async def handle_pdf_return(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info = punishment_system.get_user_info(user_id)
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

    file_path = os.path.join(BOOKS_DIR, book_name)

    try:
        if not os.path.exists(BOOKS_DIR):
            os.makedirs(BOOKS_DIR)

        pdf_file = await document.get_file()
        await pdf_file.download_to_drive(file_path)
    except Exception as e:
        error = f"Ошибка при сохранении файла: {e}"
        logger.error(error)
        await send_error_message(update, error)
        return

    punishment_system.return_book(user_id)

    await update.message.reply_text(f"Спасибо, книга '{book_name}' успешно возвращена в библиотеку!")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "list_books":
        await list_books(update, context)
    elif data.startswith("get_book:"):
        book_name = data.split("get_book:", 1)[1]
        await get_book(update, context, book_name)
    elif data == "help":
        await query.edit_message_text(help_text)
    elif data == "get_my_debt":
        await get_my_debt(update, context)
    else:
        await send_error_message(update, "Неизвестная команда.")


def main():
    global punishment_system
    # Создайте папку books рядом с этим скриптом, если ее нет
    if not os.path.exists(BOOKS_DIR):
        os.makedirs(BOOKS_DIR)

    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    punishment_system = PunishmentSystem(app.bot)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(punishment_system.start())

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.FileExtension("pdf"), handle_pdf_return))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
