# /run.py (упрощенная версия)
import gradio as gr
import atexit
import time
import sys
from ui import create_main_ui
from container import container

def cleanup_on_exit():
    print("\n👋 Завершение работы")
    
    try:
        # Останавливаем Gradio сервер
        if hasattr(sys, '_gradio_server'):
            sys._gradio_server.close()
            time.sleep(0.05)
        
    except Exception as e:
        print(f"ℹ️ Незначительная ошибка при завершении: {e}")
    
    print(f"✅ Работа приложения завершена")

def initialize_model():
    """Инициализирует модель (основную и суммаризаторы)"""
    print("\n" + "-" * 50)
    print("📦 ИНИЦИАЛИЗАЦИЯ МОДЕЛЕЙ")
    print("-" * 50)
    
    try:
        # Получаем сервис модели
        model_service = container.get_model_service()
        
        # Загружаем основную модель
        start_time = time.time()
        model, tokenizer, lock = model_service.initialize()
        load_time = time.time() - start_time
        
        if model is not None:
            print(f"✅ Основная модель загружена за {load_time:.2f} секунд")
            
            # Прогрев основной модели
            print("🔥 Прогрев основной модели...")
            try:
                warmup_messages = [{"role": "user", "content": "Привет"}]
                warmup_response = model_service.generate_response(
                    warmup_messages, 
                    max_tokens=10,
                    temperature=0.1,
                    enable_thinking=False
                )
                print("✅ Основная модель прогрета успешно")
                
            except Exception as e:
                print(f"ℹ️ Прогрев основной модели не удался: {e}, но модель загружена")
            
            # НОВОЕ: Предзагрузка суммаризаторов
            print("\n📥 ПРЕДЗАГРУЗКА СУММАРИЗАТОРОВ...")
            try:
                from services.context.summarizers import SummarizerFactory
                
                # Получаем конфиг контекста
                config = container.get_config()
                context_config = config.get("context", {})
                
                # Проверяем, включен ли контекст
                if context_config.get("enabled", True):
                    # Предзагружаем суммаризаторы
                    summarizers_config = context_config.get("summarizers", {})
                    if summarizers_config.get("preload", True):
                        success = SummarizerFactory.preload_summarizers(context_config)
                        if success:
                            print("✅ Суммаризаторы предзагружены и готовы к работе")
                        else:
                            print("⚠️ Предзагрузка суммаризаторов завершилась с ошибками")
                    else:
                        print("ℹ️ Предзагрузка суммаризаторов отключена в конфиге")
                else:
                    print("ℹ️ Контекст отключен - суммаризаторы не нужны")
                    
            except Exception as e:
                print(f"⚠️ Ошибка предзагрузки суммаризаторов: {e}")
                import traceback
                traceback.print_exc()
            
            return True
        else:
            print("❌ Не удалось загрузить основную модель")
            return False
            
    except Exception as e:
        print(f"❌ Критическая ошибка при загрузке моделей: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("🚀 ЗАПУСК QWEN3-30B-A3B CHAT")
    print("=" * 60)
        
    # Регистрируем функцию очистки при выходе
    atexit.register(cleanup_on_exit)
    
    # Загружаем конфигурация
    print("\n⚙️  ЗАГРУЗКА КОНФИГУРАЦИИ...")
    try:
        config = container.get_config()
        app_config = config.get("app", {})
        model_config = config.get("model", {})
        server_config = config.get("server", {})
        
        print(f"✅ Конфигурация загружена:")
        print(f"   Модель: {model_config.get('name', 'Qwen/Qwen3-4B')}")
    except Exception as e:
        print(f"⚠️ Ошибка загрузки конфигурации: {e}")
        return
    
    # Загружаем диалоги
    print("\n💬 ЗАГРУЗКА ДИАЛОГОВ...")
    try:
        dialog_service = container.get_dialog_service()
        dialog_count = len(dialog_service.dialogs)
        print(f"✅ Загружено диалогов: {dialog_count}")
        
    except Exception as e:
        print(f"⚠️ Ошибка загрузки диалогов: {e}")
    
    # Инициализируем модель
    model_loaded = initialize_model()
    
    if not model_loaded:
        print("\n⚠️  ВНИМАНИЕ: Модель не была загружена!")
        print("Приложение будет работать в режиме ожидания.")
        print("Модель попытается загрузиться при первом запросе.")
    
    # Создаем интерфейс
    print("\n🖥️  СОЗДАНИЕ ИНТЕРФЕЙСА...")
    try:
        demo, css_content, simple_js = create_main_ui()
        print("✅ Интерфейс создан")
    except Exception as e:
        print(f"❌ Ошибка создания интерфейса: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Запускаем сервер
    print("\n" + "=" * 60)
    print("🌐 ЗАПУСК СЕРВЕРА...")
    print("=" * 60)
    
    if model_loaded:
        print("\n⚡ Модель в памяти - готово к работе!")
    else:
        print("\n⚠️  Модель не загружена - будет загружена при первом запросе")
    
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
        print(f"❌ Ошибка запуска сервера: {e}")
        print("\n🔧 Возможные решения:")
        port = server_config.get("port", 7860)
        print(f"1. Проверьте, что порт {port} свободен")
        print("2. Попробуйте другой порт в config/app_config.yaml")
        print("3. Проверьте доступ к интернету (для загрузки модели)")

if __name__ == "__main__":
    main()