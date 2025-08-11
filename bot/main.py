import asyncio
import logging
import os
import sys
from pathlib import Path

from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from application.book import return_book
from application.button import handle_buttons
from application.starter import start
from core.settings import settings
from resources.start_bot_text import start_bot_text

logger = logging.getLogger("bot")


class ReloadHandler(FileSystemEventHandler):
    EXCLUDE_PATHS: list[str] = [
        settings.BORROWED_DATA_FILE.relative_to(settings.BASE_PATH).as_posix(),
        Path(settings.BOOKS_DIR).relative_to(settings.BASE_PATH.parent).as_posix(),
        Path(settings.LOG_FILE).relative_to(settings.BASE_PATH.parent).as_posix(),
        "__pycache__",
    ]

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def on_any_event(self, event: FileSystemEvent):
        if not any(excluded in event.src_path for excluded in self.EXCLUDE_PATHS):
            logger.info(event.src_path)
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
        logger.info(start_bot_text)
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
