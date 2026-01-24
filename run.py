# /run.py
import gradio as gr
from ui.main import create_main_ui  # Теперь возвращает (demo, css_content)
from container import container

def main():
    print("=" * 60)
    print("🚀 Запуск Qwen3-4B Chat")
    print("=" * 60)
    
    # Инициализация модели (с минимальным логированием)
    print("📦 Загрузка модели...")
    try:
        model_service = container.get_model_service()
        model, tokenizer, lock = model_service.initialize()
        # Не выводим дополнительных сообщений
    except Exception as e:
        print(f"⚠️ Предупреждение: {e}")
        print("ℹ️ Модель загрузится при первом запросе")
    
    # Создание интерфейса
    print("🖥️ Создание интерфейса...")
    demo, css_content = create_main_ui()  # ← Получаем и demo и css
    print("✅ Интерфейс создан")
    
    # Запуск приложения
    print("🌐 Запуск сервера...")
    print("=" * 60)
    
    config = container.get_config()
    
    demo.queue(
        max_size=config.queue.max_size,
        default_concurrency_limit=config.queue.concurrency_limit
    ).launch(
        server_name=config.server.host,
        server_port=config.server.port,
        share=config.server.share,
        debug=config.app.debug,
        show_error=config.server.show_error,
        theme=config.app.theme,
        css=css_content  # ← Передаем css в launch()
    )

if __name__ == "__main__":
    main()