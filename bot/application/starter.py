from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Список книг", callback_data="list_books")],
        [InlineKeyboardButton("Мой долг", callback_data="get_my_debt")],
        [InlineKeyboardButton("Помощь", callback_data="help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Это бот-библиотека.", reply_markup=reply_markup)
