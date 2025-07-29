from telegram import Update


async def send_error_message(update: Update, error_text: str):
    if update.message:
        await update.message.reply_text(error_text)
    elif update.callback_query and update.callback_query.message:
        # используем edit_message_text, если сообщение уже есть
        await update.callback_query.message.edit_text(error_text)
    else:
        print(error_text)
