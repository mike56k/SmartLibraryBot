import io
import logging

from core.settings import settings
from pdf2image import convert_from_path

logger = logging.getLogger("bot")


def get_pdf_preview_in_memory(pdf_path: str):
    try:
        # Получаем первую страницу PDF в виде изображения
        images = convert_from_path(f"{settings.BOOKS_DIR}/{pdf_path}", first_page=1, last_page=1)
        if images:
            img_byte_arr = io.BytesIO()
            images[0].save(img_byte_arr, format="JPEG")
            img_byte_arr.seek(0)  # Перемещаем указатель в начало
            return img_byte_arr
        return None
    except Exception as e:
        logger.error(f"Ошибка при создании превью кники: {e}")

    try:
        with open(settings.DEFAULT_PREVIEW_IMAGE, "rb") as f:
            default_img = io.BytesIO(f.read())
            default_img.seek(0)
            return default_img
    except Exception as e:
        logger.error(f"Не удалось загрузить стандартное изображение: {e}")
