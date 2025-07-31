from services.errors import send_error_message
from services.help import help_text
from telegram import Update
from telegram.ext import (
    ContextTypes,
)

from application.book import get_book
from application.dept import get_my_debt
from application.list import list_books


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "list_books":
        await list_books(update, context)
    elif data.startswith("get_book:"):
        book_name = data.split("get_book:", 1)[1]
        await get_book(update, context, book_name)
    elif data == "help":
        print("AAAAAAAAAAAAAAAAAa")
        await query.edit_message_text(help_text)
    elif data == "get_my_debt":
        await get_my_debt(update, context)
    else:
        await send_error_message(update, "Неизвестная команда.")
