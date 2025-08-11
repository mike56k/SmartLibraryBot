import logging.config
from functools import cached_property
from pathlib import Path
from typing import Any

from infrastructure.settings_source import ConfigSettingsSource
from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource
from services.punishment_system import PunishmentSystemService
from telegram.ext import Application, ApplicationBuilder


class Settings(BaseSettings):
    BASE_PATH: Path = Path(__file__).resolve().parent.parent
    CONFIG_FILE: Path = Path(BASE_PATH.parent / "bot.conf")
    LOG_FILE: Path = Path(BASE_PATH.parent / "bot.log")
    DEFAULT_PREVIEW_IMAGE: Path = Path(BASE_PATH / "resources/book_preview.png")
    BORROWED_DATA_FILE: Path = Path(BASE_PATH / "infrastructure/jsondb/borrowed_data.json")

    BOOKS_DIR: Path
    BOT_TOKEN: str

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """bot.conf handler"""
        return (
            init_settings,
            ConfigSettingsSource(settings_cls),
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    @computed_field
    @cached_property
    def APP(self) -> Application:  # noqa: N802
        return ApplicationBuilder().token(self.BOT_TOKEN).build()

    @computed_field
    @cached_property
    def PUNISHMENT_SYSTEM_SERVICE(self) -> PunishmentSystemService:  # noqa: N802
        return PunishmentSystemService(self.APP.bot, self.BORROWED_DATA_FILE)

    @computed_field
    @cached_property
    def LOGGER_CONFIG(self) -> dict[str, Any]:  # noqa: N802
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "verbose": {
                    "format": "[%(asctime)s] %(levelname)s %(message)s %(exc_info)s",
                }
            },
            "handlers": {
                "default": {
                    "level": "INFO",
                    "formatter": "verbose",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",  # Default is stderr
                },
                "file": {
                    "level": "INFO",
                    "class": "logging.FileHandler",
                    "filename": self.LOG_FILE,
                    "formatter": "verbose",
                },
            },
            "loggers": {
                "bot": {
                    "handlers": ["file", "default"],
                    "level": "INFO",
                    "propagate": True,
                }
            },
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }

    @field_validator("CONFIG_FILE", "LOG_FILE", "DEFAULT_PREVIEW_IMAGE", "BORROWED_DATA_FILE", "BOOKS_DIR")
    @classmethod
    def validate_path_exist(cls, value: Path) -> Path:
        if not value.exists():
            raise ValueError(f"Path does not exist: {value}")
        return value


settings = Settings()  # type: ignore
logging.config.dictConfig(settings.LOGGER_CONFIG)
