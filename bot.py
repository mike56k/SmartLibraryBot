import asyncio
import contextlib
import os

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Папка для хранения PDF книг
BOOKS_DIR = "books"

# В памяти храним, какие книги кому выданы: user_id -> book filename
borrowed_books = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Это бот-библиотека.\n"
        "Команды:\n"
        "/list - посмотреть доступные книги\n"
        "/get <название.pdf> - взять книгу\n"
        "Чтобы вернуть книгу, загрузите PDF c **корректным** названием.\n"
    )


async def list_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        files = os.listdir(BOOKS_DIR)
        pdf_files = [f for f in files if f.lower().endswith(".pdf")]
        if not pdf_files:
            await update.message.reply_text("В библиотеке нет доступных книг.")
        else:
            await update.message.reply_text("Доступные книги:\n" + "\n".join(pdf_files))
    except Exception as e:
        await update.message.reply_text(f"Ошибка при чтении каталога книг: {e}")


async def get_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Укажите название книги после команды /get")
        return
    book_name = " ".join(context.args)
    filepath = os.path.join(BOOKS_DIR, book_name)

    user_id = update.effective_user.id
    if user_id in borrowed_books:
        await update.message.reply_text("Сначала верните текущую книгу, которую взяли.")
        return

    if not os.path.isfile(filepath):
        await update.message.reply_text("Такой книги нет или она недоступна.")
        return

    # Отправляем файл
    try:
        with open(filepath, "rb") as file:
            await update.message.reply_document(document=file, filename=book_name)
    except Exception as e:
        await update.message.reply_text(f"Ошибка при отправке книги: {e}")
        return

    # Удаляем файл с каталога доступных книг, фиксируем выдачу
    os.remove(filepath)
    borrowed_books[user_id] = book_name

    await update.message.reply_text(f"Вы взяли книгу '{book_name}'. Пожалуйста, верните её позже!")

    # Запускаем таймер напоминания (здесь 60 секунд — можно увеличить)
    asyncio.create_task(remind_return(context.bot, user_id, book_name))  # noqa: RUF006


async def remind_return(bot, user_id, book_name):
    await asyncio.sleep(60)  # Время ожидания перед напоминанием (секунды)
    if borrowed_books.get(user_id) == book_name:
        with contextlib.suppress(Exception):
            await bot.send_message(
                chat_id=user_id,
                text=(f"Пожалуйста, не забудьте вернуть книгу '{book_name}'. Отправьте PDF файла с командой /return."),
            )


async def handle_pdf_return(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"borrowed_books keys: {list(borrowed_books.keys())}, current user_id: {user_id}")
    if user_id not in borrowed_books:
        await update.message.reply_text("У вас нет взятых книг для возврата.")
        return

    # Проверяем, что пользователь прислал PDF файл
    if update.message.document is None or not update.message.document.file_name.lower().endswith(".pdf"):
        await update.message.reply_text("Пожалуйста, загрузите PDF файл с книгой для возврата.")
        return

    book_name = borrowed_books[user_id]
    file_path = os.path.join(BOOKS_DIR, book_name)

    # Скачиваем файл
    pdf_file = await update.message.document.get_file()
    await pdf_file.download_to_drive(file_path)

    # Убираем отметку о выданной книге
    del borrowed_books[user_id]
    await update.message.reply_text(f"Спасибо, книга '{book_name}' успешно возвращена в библиотеку!")


def main():
    # Создайте папку books рядом с этим скриптом, если ее нет
    if not os.path.exists(BOOKS_DIR):
        os.makedirs(BOOKS_DIR)

    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_books))
    app.add_handler(CommandHandler("get", get_book))
    app.add_handler(MessageHandler(filters.Document.FileExtension("pdf"), handle_pdf_return))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
