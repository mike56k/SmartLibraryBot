import asyncio
import logging
import os
import sys

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
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger("bot")


class ReloadHandler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def on_any_event(self, event: FileSystemEvent):
        logger.info("Изменение обнаружено, перезапускаем бота...")
        self.loop.call_soon_threadsafe(self.restart)

    def restart(self):
        logger.info("Перезапуск процесса...")
        python = sys.executable
        os.execv(python, [python] + sys.argv)


def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    observer = Observer()
    handler = ReloadHandler(loop)
    observer.schedule(handler, path=".", recursive=True)  # отслеживаем папку проекта
    observer.start()

    try:
        # Запускаете бота (или ваши задачи, например, polling)
        loop.run_until_complete(settings.PUNISHMENT_SYSTEM_SERVICE.start())
        logger.info("БОТИНОК ЗАПУЩЕНОМАНЭ")

        settings.APP.add_handler(CommandHandler("start", start))
        settings.APP.add_handler(CallbackQueryHandler(handle_buttons))
        settings.APP.add_handler(MessageHandler(filters.Document.FileExtension("pdf"), return_book))

        settings.APP.run_polling()

    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()
