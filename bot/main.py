import asyncio

from application.book import return_book
from application.button import handle_buttons
from application.starter import start
from core.settings import settings
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)


def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print(settings.BOT_TOKEN)
    loop.run_until_complete(settings.PUNISHMENT_SYSTEM_SERVICE.start())

    settings.APP.add_handler(CommandHandler("start", start))
    settings.APP.add_handler(CallbackQueryHandler(handle_buttons))
    settings.APP.add_handler(MessageHandler(filters.Document.FileExtension("pdf"), return_book))

    settings.APP.run_polling()


if __name__ == "__main__":
    main()
