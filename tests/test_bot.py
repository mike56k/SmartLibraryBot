import os
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from telegram import Update, Message, User, Document
from telegram.ext import ContextTypes

import bot


@pytest.fixture
def mocked_update_start():
    user = User(id=123, first_name="TestUser", is_bot=False)
    message = MagicMock(spec=Message)
    message.from_user = user
    message.reply_text = AsyncMock()
    update = Update(update_id=1, message=message)
    return update

@pytest.mark.asyncio
async def test_start_command(mocked_update_start):
    context = MagicMock()
    await bot.start(mocked_update_start, context)
    mocked_update_start.message.reply_text.assert_called()
    reply_text = mocked_update_start.message.reply_text.call_args[0][0]
    assert "Привет" in reply_text
    assert "/list" in reply_text
    assert "/get" in reply_text

@pytest.mark.asyncio
async def test_list_books_empty(monkeypatch, mocked_update_start):
    monkeypatch.setattr(bot, "BOOKS_DIR", "empty_books_dir")
    if not os.path.exists("empty_books_dir"):
        os.makedirs("empty_books_dir")
    # Очистка папки, если что
    for f in os.listdir("empty_books_dir"):
        os.remove(os.path.join("empty_books_dir", f))

    context = MagicMock()
    await bot.list_books(mocked_update_start, context)
    mocked_update_start.message.reply_text.assert_called_with("В библиотеке нет доступных книг.")

@pytest.mark.asyncio
async def test_get_book_no_args(mocked_update_start):
    context = MagicMock()
    context.args = []
    await bot.get_book(mocked_update_start, context)
    mocked_update_start.message.reply_text.assert_called_with("Укажите название книги после команды /get")

@pytest.mark.asyncio
async def test_get_book_not_exist(monkeypatch, mocked_update_start):
    context = MagicMock()
    context.args = ["not_exist.pdf"]
    monkeypatch.setattr(bot, "BOOKS_DIR", "empty_books_dir")
    
    await bot.get_book(mocked_update_start, context)
    mocked_update_start.message.reply_text.assert_called_with("Такой книги нет или она недоступна.")

@pytest.mark.asyncio
async def test_handle_pdf_return_success(monkeypatch):
    user = User(id=123, first_name="TestUser", is_bot=False)
    message = MagicMock(spec=Message)
    message.from_user = user
    # Задаём документ с PDF
    message.document = MagicMock(spec=Document)
    message.document.file_name = "test_book.pdf"
    message.document.get_file = AsyncMock()
    file_mock = AsyncMock()
    file_mock.download_to_drive = AsyncMock()
    message.document.get_file.return_value = file_mock
    message.reply_text = AsyncMock()

    update = Update(update_id=1, message=message)
    context = MagicMock()

    # Помечаем у пользователя взятую книгу
    bot.borrowed_books[user.id] = "test_book.pdf"
    monkeypatch.setattr(bot, "BOOKS_DIR", "empty_books_dir")
    if not os.path.exists("empty_books_dir"):
        os.makedirs("empty_books_dir")

    await bot.handle_pdf_return(update, context)

    message.reply_text.assert_called_with("Спасибо, книга 'test_book.pdf' успешно возвращена в библиотеку!")
    assert user.id not in bot.borrowed_books
    file_mock.download_to_drive.assert_called_once()

@pytest.mark.asyncio
async def test_handle_pdf_return_no_borrowed_book():
    user = User(id=123, first_name="TestUser", is_bot=False)
    message = MagicMock(spec=Message)
    message.from_user = user
    message.document = MagicMock(spec=Document)
    message.document.file_name = "test_book.pdf"
    message.reply_text = AsyncMock()

    update = Update(update_id=1, message=message)
    context = MagicMock()

    # У пользователя нет взятых книг
    bot.borrowed_books.pop(user.id, None)

    await bot.handle_pdf_return(update, context)

    message.reply_text.assert_called_with("У вас нет взятых книг для возврата.")

@pytest.mark.asyncio
async def test_handle_pdf_return_wrong_file_type(monkeypatch):
    user = User(id=123, first_name="TestUser", is_bot=False)
    message = MagicMock(spec=Message)
    message.from_user = user
    # Прислан не pdf
    message.document = MagicMock(spec=Document)
    message.document.file_name = "not_pdf.txt"
    message.reply_text = AsyncMock()

    update = Update(update_id=1, message=message)
    context = MagicMock()

    # Пользователь взял книгу
    bot.borrowed_books[user.id] = "some_book.pdf"

    await bot.handle_pdf_return(update, context)

    message.reply_text.assert_called_with("Пожалуйста, загрузите PDF файл с книгой для возврата.")
