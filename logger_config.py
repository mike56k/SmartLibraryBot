import logging
import sys

# Создаём логгер
logger = logging.getLogger()
logger.setLevel(logging.ERROR)  # Уровень логирования (можно поменять)

# Создаём обработчик вывода в stdout
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.ERROR)  # Уровень логирования для обработчика

# Форматтер для читаемого вывода
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
stdout_handler.setFormatter(formatter)

# Добавляем обработчик к логгеру
logger.addHandler(stdout_handler)
