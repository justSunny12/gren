# services/logger.py
import sys
from loguru import logger
from typing import Optional, Any


class LoggerWrapper:
    """Обёртка для loguru с поддержкой %-форматирования и kwargs."""

    def __init__(self, logger_instance):
        self._logger = logger_instance

    def _log(self, level: str, msg: str, *args, **kwargs):
        """Общий метод логирования с поддержкой exc_info."""
        if args:
            formatted = msg % args
        else:
            formatted = msg

        # Извлекаем exc_info из kwargs, если есть
        exc_info = kwargs.pop('exc_info', None)
        if exc_info:
            self._logger.opt(exception=exc_info).log(level, formatted)
        else:
            self._logger.log(level, formatted)

    def error(self, msg: str, *args, **kwargs):
        self._log("ERROR", msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self._log("WARNING", msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self._log("INFO", msg, *args, **kwargs)

    def stats(self, msg: str, *args, **kwargs):
        self._log("STATS", msg, *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs):
        self._log("DEBUG", msg, *args, **kwargs)

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
            's': 'STATS',
            'd': 'DEBUG'
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