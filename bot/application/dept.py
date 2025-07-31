from datetime import datetime

from core.settings import settings
from services.errors import send_error_message
from telegram import Update
from telegram.ext import (
    ContextTypes,
)


async def get_my_debt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info = settings.PUNISHMENT_SYSTEM_SERVICE.get_user_info(user_id)
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
