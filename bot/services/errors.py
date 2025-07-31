import logging

from telegram import Update

logger = logging.getLogger("bot")


async def send_error_message(update: Update, error_text: str):
    if getattr(update, "message", None):
        await update.message.reply_text(error_text)
    elif (
        getattr(update, "callback_query", None)
        and getattr(update.callback_query, "message", None)
        and hasattr(update.callback_query.message, "edit_text")
    ):
        try:
            await update.callback_query.message.edit_text(error_text)
        except Exception:
            await update.callback_query.answer(error_text, show_alert=True)
    elif getattr(update, "callback_query", None):
        await update.callback_query.answer(error_text, show_alert=True)
    else:
        logger.error(f"{error_text} - не удалось отправить сообщение")
