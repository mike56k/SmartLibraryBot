import os
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from punishment_system import PunishmentSystem
from datetime import datetime, timedelta

@pytest.fixture
def mock_bot():
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    return bot

@pytest.fixture
def punishment_system(tmp_path, mock_bot):
    # Используем временную папку для данных, чтобы не писать в реальный файл
    data_file = tmp_path / "borrowed_data.json"
    rs = PunishmentSystem(
        bot=mock_bot,
        reminder_interval_minutes=0.01,  # маленький интервал для быстрого теста
        max_borrow_days=1,  # 1 день для простоты теста
        fine_per_day=5
    )
    # Переопределим путь к файлу для теста
    rs.DATA_FILE = str(data_file)
    rs.borrowed_books = {}
    return rs

@pytest.mark.asyncio
async def test_add_and_return_book(punishment_system):
    user_id = 123
    book_name = "test_book.pdf"

    # Добавляем книгу
    punishment_system.add_borrow(user_id, book_name)
    assert str(user_id) in punishment_system.borrowed_books
    record = punishment_system.borrowed_books[str(user_id)]
    assert record["book"] == book_name
    assert record["fine"] == 0

    # Возвращаем книгу
    punishment_system.return_book(user_id)
    assert str(user_id) not in punishment_system.borrowed_books

@pytest.mark.asyncio
async def test_save_and_load(tmp_path, mock_bot):
    data_file = tmp_path / "b.json"
    rs = PunishmentSystem(bot=mock_bot)
    rs.DATA_FILE = str(data_file)

    rs.borrowed_books = {"1": {"book": "b.pdf", "borrowed_at": datetime.utcnow().isoformat(), "fine": 0}}
    rs._save_data()
    # Создаём новый объект и проверяем загрузку
    rs2 = PunishmentSystem(bot=mock_bot)
    rs2.DATA_FILE = str(data_file)
    rs2._load_data()
    assert rs2.borrowed_books == rs.borrowed_books

@pytest.mark.asyncio
async def test_reminder_loop_sends_message_and_updates_fine(punishment_system, mock_bot):
    user_id = "111"
    # borrow date 2 дня назад, должно вызвать штраф
    borrowed_at = (datetime.utcnow() - timedelta(days=2)).isoformat()
    punishment_system.borrowed_books[user_id] = {
        "book": "book.pdf",
        "borrowed_at": borrowed_at,
        "fine": 0
    }

    punishment_system._running = True

    # Запускаем _reminder_loop один раз (через patch asyncio.sleep чтобы не ждать)
    with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
        # принудительно завершим цикл после первого прохода
        async def stop_loop():
            punishment_system._running = False
        mock_sleep.side_effect = stop_loop

        await punishment_system._reminder_loop(user_id)

    # Проверяем, что бот отправил сообщение
    mock_bot.send_message.assert_called_once()
    args, kwargs = mock_bot.send_message.call_args
    assert int(user_id) == kwargs['chat_id']
    assert "штраф" in kwargs['text'].lower()

    # Проверяем, что штраф обновился в данных
    assert punishment_system.borrowed_books[user_id]["fine"] > 0

@pytest.mark.asyncio
async def test_reminder_loop_no_fine_before_due(punishment_system, mock_bot):
    user_id = "222"
    borrowed_at = (datetime.utcnow() - timedelta(hours=12)).isoformat()  # меньше 1 дня
    punishment_system.borrowed_books[user_id] = {
        "book": "book2.pdf",
        "borrowed_at": borrowed_at,
        "fine": 0
    }
    punishment_system._running = True

    with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
        async def stop_loop():
            punishment_system._running = False
        mock_sleep.side_effect = stop_loop

        await punishment_system._reminder_loop(user_id)

    mock_bot.send_message.assert_called_once()
    # Штраф должен быть 0
    assert punishment_system.borrowed_books[user_id]["fine"] == 0

@pytest.mark.asyncio
async def test_ensure_task_creates_task(punishment_system):
    user_id = "333"
    punishment_system.borrowed_books[user_id] = {
        "book": "book3.pdf",
        "borrowed_at": datetime.utcnow().isoformat(),
        "fine": 0
    }
    punishment_system._running = True
    punishment_system._tasks.clear()

    punishment_system._ensure_task(user_id)
    assert user_id in punishment_system._tasks
    task = punishment_system._tasks[user_id]
    assert not task.done()

    # Очистим задачу
    task.cancel()
