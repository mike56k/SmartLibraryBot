import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

from telegram.ext import Application


class PunishmentSystemService:
    """
    Класс для управления выдачей книг, напоминаниями и штрафами.
    """

    def __init__(
        self,
        bot: Application,
        borrowed_data_file: Path,
        reminder_interval_minutes: int = 60 * 24,
        max_borrow_days: int = 14,
        fine_per_day: int = 10,
    ):
        """
        :param bot: экземпляр telegram.Bot для отправки сообщений.
        :param reminder_interval_minutes: интервал периодического напоминания в минутах.
        :param max_borrow_days: максимальный срок заимствования книги без штрафа.
        :param fine_per_day: сумма штрафа за каждый день просрочки.
        """
        self.bot = bot
        self.borrowed_data_file = borrowed_data_file
        self.reminder_interval = timedelta(minutes=reminder_interval_minutes)
        self.max_borrow_period = timedelta(days=max_borrow_days)
        self.fine_per_day = fine_per_day

        # Структура данных: {user_id (str): {"book": str, "borrowed_at": ISO str, "fine": int}}
        self.borrowed_books = {}

        self._load_data()
        self._tasks = {}
        self._running = False

    def _load_data(self):
        with open(self.borrowed_data_file, encoding="utf-8") as f:
            self.borrowed_books = json.load(f)

    def _save_data(self):
        with open(self.borrowed_data_file, "w", encoding="utf-8") as f:
            json.dump(self.borrowed_books, f, ensure_ascii=False, indent=2)

    async def start(self):
        """
        Запуск задачи периодических напоминаний.
        """
        self._running = True
        for user_id in list(self.borrowed_books.keys()):
            self._ensure_task(user_id)
        asyncio.create_task(self._periodic_check_loop())  # noqa: RUF006

    async def stop(self):
        """
        Остановка всех задач.
        """
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()

    def add_borrow(self, user_id: int, book_name: str):
        """
        Добавить запись о выданной книге пользователю с текущим временем.
        Старые напоминания для пользователя сбрасываются.
        """
        user_id_str = str(user_id)
        now = datetime.utcnow().isoformat()
        self.borrowed_books[user_id_str] = {"book": book_name, "borrowed_at": now, "fine": 0}
        self._save_data()
        self._ensure_task(user_id_str)

    def return_book(self, user_id: int):
        """
        Пользователь вернул книгу — удаляем запись и прекращаем напоминания.
        """
        user_id_str = str(user_id)
        if user_id_str in self.borrowed_books:
            self.borrowed_books.pop(user_id_str)
            self._save_data()
            if user_id_str in self._tasks:
                task = self._tasks[user_id_str]
                task.cancel()
                del self._tasks[user_id_str]

    def get_user_info(self, user_id: int):
        """
        Вернуть информацию о пользователе и книгах, штрафах.
        """
        return self.borrowed_books.get(str(user_id), None)

    def _ensure_task(self, user_id_str: str):
        """
        Запустить задачу напоминаний, если её нет.
        """
        if user_id_str in self._tasks:
            # Задача уже запущена
            return
        task = asyncio.create_task(self._reminder_loop(user_id_str))
        self._tasks[user_id_str] = task

    async def _reminder_loop(self, user_id_str: str):
        """
        Задача, которая периодически напоминает пользователю и начисляет штрафы.
        """
        while self._running and user_id_str in self.borrowed_books:
            record = self.borrowed_books[user_id_str]
            book_name = record["book"]
            borrowed_at = datetime.fromisoformat(record["borrowed_at"])
            now = datetime.utcnow()

            # Время просрочки
            overdue = (now - borrowed_at) - self.max_borrow_period
            overdue_days = overdue.days if overdue > timedelta(0) else 0

            # Начисляем штраф
            if overdue_days > 0:
                fine = overdue_days * self.fine_per_day
                if record.get("fine", 0) != fine:
                    record["fine"] = fine
                    self._save_data()
            else:
                record["fine"] = 0
                self._save_data()

            # Формируем сообщение пользователю
            msg = f"Напоминание: книга '{book_name}' взята вами {borrowed_at.date()}. "
            if overdue_days > 0:
                msg += (
                    f"Срок возврата истек {overdue_days} дн. назад. Штраф: {record['fine']} у.е. "
                    f"Пожалуйста, верните книгу как можно скорее."
                )
            else:
                days_left = (borrowed_at + self.max_borrow_period - now).days
                msg += f"Пожалуйста, верните книгу в течение {days_left} дн."

            try:
                await self.bot.send_message(chat_id=int(user_id_str), text=msg)
            except Exception as e:
                print(f"Ошибка отправки напоминания пользователю {user_id_str}: {e}")

            # Ждём следующий интервал
            await asyncio.sleep(self.reminder_interval.total_seconds())

    async def _periodic_check_loop(self):
        """
        Общая задача для периодической проверки и запуска задач напоминаний.
        (Для случаев новых пользователей среди существующих). Не обязательна при _ensure_task.
        """
        while self._running:
            for user_id_str in list(self.borrowed_books.keys()):
                self._ensure_task(user_id_str)
            await asyncio.sleep(60 * 10)  # проверять каждые 10 минут
