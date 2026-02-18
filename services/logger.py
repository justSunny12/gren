# services/logger.py
import sys
from loguru import logger
from typing import Optional


class LoggerWrapper:
    """Обёртка для loguru с поддержкой %-форматирования."""

    def __init__(self, logger_instance):
        self._logger = logger_instance

    def error(self, msg: str, *args):
        """Логирует ошибку с поддержкой %-форматирования."""
        if args:
            self._logger.error(msg % args)
        else:
            self._logger.error(msg)

    def warning(self, msg: str, *args):
        """Логирует предупреждение с поддержкой %-форматирования."""
        if args:
            self._logger.warning(msg % args)
        else:
            self._logger.warning(msg)

    def info(self, msg: str, *args):
        """Логирует информацию с поддержкой %-форматирования."""
        if args:
            self._logger.info(msg % args)
        else:
            self._logger.info(msg)

    def stats(self, msg: str, *args):
        """Логирует статистику (кастомный уровень STATS) с поддержкой %-форматирования."""
        if args:
            self._logger.log("STATS", msg % args)
        else:
            self._logger.log("STATS", msg)

    def configure(self, level_string: str):
        """Перенастраивает логгер под новый уровень (регистронезависимо)."""
        self._logger.remove()
        # Регистрируем кастомный уровень STATS, если ещё не зарегистрирован
        try:
            self._logger.level("STATS", no=25, color="<cyan>")
        except ValueError:
            pass

        # Приводим к нижнему регистру для сопоставления
        allowed = set(level_string.lower().strip())
        level_map = {
            'e': 'ERROR',
            'w': 'WARNING',
            'i': 'INFO',
            's': 'STATS'
        }
        allowed_names = {level_map[ch] for ch in allowed if ch in level_map}

        def stdout_filter(record):
            return record["level"].name in allowed_names and record["level"].name != "ERROR"

        def stderr_filter(record):
            return record["level"].name == "ERROR" and "ERROR" in allowed_names

        fmt = "{time:YYYY-MM-DD HH:mm:ss.SSS} [{level}] {message}"
        self._logger.add(sys.stdout, format=fmt, filter=stdout_filter, level=0)
        self._logger.add(sys.stderr, format=fmt, filter=stderr_filter, level=0)


def setup_logger(level_string: str = "ewi") -> LoggerWrapper:
    """Создаёт и настраивает логгер с указанным уровнем."""
    wrapper = LoggerWrapper(logger)
    wrapper.configure(level_string)
    return wrapper


def create_logger_from_config(config_service):
    """Создаёт логгер на основе конфигурации приложения."""
    app_config = config_service.get_config().get('app', {})
    level = app_config.get('logging_level', 'ewis')
    return setup_logger(level)