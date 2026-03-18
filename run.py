# /run.py
import atexit
import time
import sys
import asyncio
import os

from container import container
from ui import create_main_ui
from services.context.global_manager import global_summary_manager


def cleanup_on_exit():
    """Завершение работы приложения."""
    try:
        logger = container.get("logger")
        logger.info("👋 Завершение работы")
        # Останавливаем глобальный воркер суммаризации
        global_summary_manager.stop()
        if hasattr(sys, '_gradio_server'):
            sys._gradio_server.close()
            time.sleep(0.05)
    except Exception as e:
        # Запасной вариант, если логгер уже не работает
        print(f"ℹ️ Незначительная ошибка при завершении: {e}")
    finally:
        try:
            logger = container.get("logger")
            logger.info("✅ Работа приложения завершена")
        except:
            pass


async def warmup_model_async(model_service, logger):
    """Асинхронный прогрев модели через stream_response."""
    warmup_messages = [{"role": "user", "content": "Привет"}]
    try:
        async for _ in model_service.stream_response(
            messages=warmup_messages,
            max_tokens=10,
            temperature=0.1,
            enable_thinking=False
        ):
            pass
        logger.info("   ✅ Прогрев основной модели завершён успешно")
    except Exception as e:
        logger.warning("   ℹ️ Прогрев основной модели не удался: %s, но модель загружена", e)


def initialize_model(logger):
    """Инициализирует модель (основную и суммаризатор)."""
    logger.info("-" * 50)
    logger.info("📦 ИНИЦИАЛИЗАЦИЯ МОДЕЛЕЙ")
    logger.info("-" * 50)

    try:
        model_service = container.get_model_service()
        start_time = time.time()
        model, tokenizer, lock = model_service.initialize()
        load_time = time.time() - start_time

        if model is not None:
            logger.info("   ✅ Основная модель загружена за %.2f секунд", load_time)

            # Прогрев основной модели
            try:
                asyncio.run(warmup_model_async(model_service, logger))
            except RuntimeError as e:
                logger.warning("   ⚠️ Не удалось запустить асинхронный прогрев: %s", e)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(warmup_model_async(model_service, logger))

            # Предзагрузка суммаризатора
            try:
                from services.context.summarizer_factory import SummarizerFactory
                config = container.get_config()
                context_config = config.get("context", {})

                if context_config.get("enabled", True):
                    model_config = context_config.get("model", {})
                    local_path = model_config.get("local_path")
                    if not local_path or not os.path.exists(local_path):
                        logger.error("   ❌ Локальный путь для модели суммаризации не найден: %s", local_path)
                        logger.error("   ❌ Суммаризация отключена. Укажите правильный local_path в context_config.yaml")
                        return True

                    loading_config = context_config.get("loading", {})
                    if loading_config.get("preload", True):
                        success = SummarizerFactory.preload_summarizers(context_config)
                        if success:
                            logger.info("   ✅ Предзагрузка суммаризатора выполнена")
                        else:
                            logger.error("   ❌ Предзагрузка суммаризатора завершилась с ошибками")
                    else:
                        logger.info("   ℹ️ Предзагрузка суммаризатора отключена в конфиге")
                else:
                    logger.info("   ℹ️ Контекст отключён — суммаризатор не нужен")

            except Exception as e:
                logger.error("   ❌ Ошибка предзагрузки суммаризатора: %s", e)
                import traceback
                traceback.print_exc()

            return True
        else:
            logger.error("   ❌ Не удалось загрузить основную модель")
            return False

    except Exception as e:
        logger.error("   ❌ Критическая ошибка при загрузке моделей: %s", e)
        import traceback
        traceback.print_exc()
        return False


def main():
    # Получаем логгер (изначально настроен на уровень "ewi" — значение по умолчанию)
    logger = container.get("logger")

    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК QWEN3-30B-A3B CHAT")
    logger.info("=" * 60)

    atexit.register(cleanup_on_exit)

    logger.info("⚙️  ЗАГРУЗКА КОНФИГУРАЦИИ...")
    try:
        config = container.get_config()
        app_config = config.get("app", {})
        server_config = config.get("server", {})

        # Перенастраиваем логгер согласно уровню из конфига
        new_level = app_config.get("logging_level", "ewis")
        logger.configure(new_level)
        logger.info("   ✅ Конфигурация загружена успешно")
        logger.info("      Уровень логирования: %s", new_level)
    except Exception as e:
        logger.error("⚠️ Ошибка загрузки конфигурации: %s", e)
        return

    logger.info("💬 ЗАГРУЗКА ДИАЛОГОВ...")
    try:
        dialog_service = container.get_dialog_service()
        dialog_count = len(dialog_service.dialogs)
        logger.info("   ✅ Загружено диалогов: %d", dialog_count)
    except Exception as e:
        logger.error("⚠️ Ошибка загрузки диалогов: %s", e)

    model_loaded = initialize_model(logger)

    if not model_loaded:
        logger.warning("⚠️  ВНИМАНИЕ: Модель не была загружена!")
        logger.warning("Приложение будет работать в режиме ожидания.")
        logger.warning("Модель попытается загрузиться при первом запросе.")

    # Запуск глобального воркера суммаризации
    logger.info("🔄 Запуск глобального воркера суммаризаций...")
    try:
        global_summary_manager.start()
        logger.info("   ✅ Воркер запущен")
    except Exception as e:
        logger.error("   ❌ Ошибка запуска воркера: %s", e)

    logger.info("=" * 60)
    logger.info("🌐 ЗАПУСК СЕРВЕРА...")
    logger.info("=" * 60)

    logger.info("🖥️  СОЗДАНИЕ ИНТЕРФЕЙСА...")
    try:
        demo, css_content, simple_js = create_main_ui()
        logger.info("   ✅ Интерфейс создан")
    except Exception as e:
        logger.error("   ❌ Ошибка создания интерфейса: %s", e)
        import traceback
        traceback.print_exc()
        return

    if model_loaded:
        logger.info("   ✅ Модель загружена, готова к работе")
    else:
        logger.warning("   ⚠️  Модель не загружена — будет загружена при первом запросе")

    try:
        queue_config = config.get("queue", {})
        demo.queue(
            max_size=queue_config.get("max_size", 5),
            default_concurrency_limit=queue_config.get("concurrency_limit", 1)
        ).launch(
            server_name=server_config.get("host", "0.0.0.0"),
            server_port=server_config.get("port", 7860),
            share=server_config.get("share", False),
            debug=app_config.get("debug", False),
            show_error=server_config.get("show_error", True),
            theme=app_config.get("theme", "soft"),
            css=css_content,
            head=simple_js
        )
    except Exception as e:
        logger.error("❌ Ошибка запуска сервера: %s", e)
        logger.error("🔧 Возможные решения:")
        port = server_config.get("port", 7860)
        logger.error("1. Проверьте, что порт %d свободен", port)
        logger.error("2. Попробуйте другой порт в config/app_config.yaml")
        logger.error("3. Проверьте доступ к интернету (для загрузки модели)")


if __name__ == "__main__":
    main()