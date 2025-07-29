async def send_error_message(update, error_text):
    # Если это обычное сообщение — отправляем новое текстовое сообщение
    if update.message:
        await update.message.reply_text(error_text)

    # Если это callback_query, пытаемся отредактировать сообщение,
    # но если это невозможно — отправляем новое сообщение
    elif update.callback_query:
        try:
            if update.callback_query.message and update.callback_query.message.text:
                await update.callback_query.message.edit_text(error_text)
            else:
                # Если нет текста для редактирования — отправим новое сообщение
                await update.callback_query.message.reply_text(error_text)
        except Exception:
            # Если редактирование завершилось ошибкой, отправляем новое сообщение
            await update.callback_query.message.reply_text(error_text)

    else:
        # На всякий случай, если update не содержит message и callback_query
        print(error_text)
