import pytest
from unittest.mock import AsyncMock, patch

from services.settings.PUNISHMENT_SYSTEM_SERVICE import PunishmentSystem
from datetime import datetime, timedelta

@pytest.fixture
def mock_bot():
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    return bot

@pytest.fixture
def settings.PUNISHMENT_SYSTEM_SERVICE(tmp_path, mock_bot):
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
async def test_add_and_return_book(settings.PUNISHMENT_SYSTEM_SERVICE):
    user_id = 123
    book_name = "test_book.pdf"

    # Добавляем книгу
    settings.PUNISHMENT_SYSTEM_SERVICE.add_borrow(user_id, book_name)
    assert str(user_id) in settings.PUNISHMENT_SYSTEM_SERVICE.borrowed_books
    record = settings.PUNISHMENT_SYSTEM_SERVICE.borrowed_books[str(user_id)]
    assert record["book"] == book_name
    assert record["fine"] == 0

    # Возвращаем книгу
    settings.PUNISHMENT_SYSTEM_SERVICE.return_book(user_id)
    assert str(user_id) not in settings.PUNISHMENT_SYSTEM_SERVICE.borrowed_books

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
async def test_reminder_loop_sends_message_and_updates_fine(settings.PUNISHMENT_SYSTEM_SERVICE, mock_bot):
    user_id = "111"
    # borrow date 2 дня назад, должно вызвать штраф
    borrowed_at = (datetime.utcnow() - timedelta(days=2)).isoformat()
    settings.PUNISHMENT_SYSTEM_SERVICE.borrowed_books[user_id] = {
        "book": "book.pdf",
        "borrowed_at": borrowed_at,
        "fine": 0
    }

    settings.PUNISHMENT_SYSTEM_SERVICE._running = True

    # Запускаем _reminder_loop один раз (через patch asyncio.sleep чтобы не ждать)
    with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
        # принудительно завершим цикл после первого прохода
        async def stop_loop():
            settings.PUNISHMENT_SYSTEM_SERVICE._running = False
        mock_sleep.side_effect = stop_loop

        await settings.PUNISHMENT_SYSTEM_SERVICE._reminder_loop(user_id)

    # Проверяем, что бот отправил сообщение
    mock_bot.send_message.assert_called_once()
    args, kwargs = mock_bot.send_message.call_args
    assert int(user_id) == kwargs['chat_id']
    assert "штраф" in kwargs['text'].lower()

    # Проверяем, что штраф обновился в данных
    assert settings.PUNISHMENT_SYSTEM_SERVICE.borrowed_books[user_id]["fine"] > 0

@pytest.mark.asyncio
async def test_reminder_loop_no_fine_before_due(settings.PUNISHMENT_SYSTEM_SERVICE, mock_bot):
    user_id = "222"
    borrowed_at = (datetime.utcnow() - timedelta(hours=12)).isoformat()  # меньше 1 дня
    settings.PUNISHMENT_SYSTEM_SERVICE.borrowed_books[user_id] = {
        "book": "book2.pdf",
        "borrowed_at": borrowed_at,
        "fine": 0
    }
    settings.PUNISHMENT_SYSTEM_SERVICE._running = True

    with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
        async def stop_loop():
            settings.PUNISHMENT_SYSTEM_SERVICE._running = False
        mock_sleep.side_effect = stop_loop

        await settings.PUNISHMENT_SYSTEM_SERVICE._reminder_loop(user_id)

    mock_bot.send_message.assert_called_once()
    # Штраф должен быть 0
    assert settings.PUNISHMENT_SYSTEM_SERVICE.borrowed_books[user_id]["fine"] == 0

@pytest.mark.asyncio
async def test_ensure_task_creates_task(settings.PUNISHMENT_SYSTEM_SERVICE):
    user_id = "333"
    settings.PUNISHMENT_SYSTEM_SERVICE.borrowed_books[user_id] = {
        "book": "book3.pdf",
        "borrowed_at": datetime.utcnow().isoformat(),
        "fine": 0
    }
    settings.PUNISHMENT_SYSTEM_SERVICE._running = True
    settings.PUNISHMENT_SYSTEM_SERVICE._tasks.clear()

    settings.PUNISHMENT_SYSTEM_SERVICE._ensure_task(user_id)
    assert user_id in settings.PUNISHMENT_SYSTEM_SERVICE._tasks
    task = settings.PUNISHMENT_SYSTEM_SERVICE._tasks[user_id]
    assert not task.done()

    # Очистим задачу
    task.cancel()
