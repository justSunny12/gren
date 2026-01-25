# /run.py (полностью исправленный)
import gradio as gr
import atexit
import time
from ui.main import create_main_ui
from container import container

def print_memory_stats(prefix: str = ""):
    """Выводит статистику памяти"""
    try:
        import psutil
        import torch
        
        process = psutil.Process()
        memory_info = process.memory_info()
        
        ram_used = memory_info.rss / 1024**3
        ram_percent = process.memory_percent()
        
        print(f"{prefix}💾 RAM: {ram_used:.2f} GB ({ram_percent:.1f}%)")
        
        if torch.cuda.is_available():
            gpu_used = torch.cuda.memory_allocated() / 1024**3
            gpu_cached = torch.cuda.memory_reserved() / 1024**3
            print(f"{prefix}🎮 GPU: {gpu_used:.2f} GB / кэш: {gpu_cached:.2f} GB")
        
    except Exception as e:
        print(f"{prefix}⚠️ Не удалось получить статистику памяти: {e}")

def cleanup_on_exit():
    """Только при завершении приложения - ПОЛНАЯ очистка"""
    print("\n" + "=" * 50)
    print("🔚 ЗАВЕРШЕНИЕ РАБОТЫ ПРИЛОЖЕНИЯ")
    print("=" * 50)
    
    try:
        # Полная очистка ВСЕХ ресурсов
        container.force_cleanup_all()
        
        # Даем время на освобождение памяти
        time.sleep(0.3)
        
        print("✅ Все ресурсы освобождены из памяти")
        print("👋 Работа приложения завершена")
        
    except Exception as e:
        print(f"⚠️ Ошибка при завершении: {e}")
    
    print("=" * 50)

def initialize_model():
    """Инициализирует модель один раз при старте"""
    print("\n" + "-" * 50)
    print("📦 ИНИЦИАЛИЗАЦИЯ МОДЕЛИ")
    print("-" * 50)
    
    try:
        # Получаем сервис модели
        model_service = container.get_model_service()
        
        print(f"📊 Используется: {type(model_service).__name__}")
        
        # Получаем конфигурацию для отображения примененных настроек
        config = container.get_config()
        user_settings = container.get("config_service").get_user_settings()
        
        if user_settings:
            print(f"📝 Применены пользовательские настройки:")
            if "generation" in user_settings:
                gen = user_settings["generation"]
                if "max_tokens" in gen:
                    print(f"   Токены: {gen['max_tokens']}")
                if "temperature" in gen:
                    print(f"   Температура: {gen['temperature']}")
                if "enable_thinking" in gen:
                    print(f"   Thinking: {gen['enable_thinking']}")
        
        # Выводим память до загрузки
        print_memory_stats("До загрузки модели: ")
        
        # Загружаем модель
        start_time = time.time()
        model, tokenizer, lock = model_service.initialize()
        load_time = time.time() - start_time
        
        if model is not None:
            print(f"✅ Модель загружена за {load_time:.2f} секунд")
            print("💾 Модель останется в памяти для быстрых ответов")
            
            # Память после загрузки
            print_memory_stats("После загрузки модели: ")
            
            # Прогрев модели С ВЫКЛЮЧЕННЫМИ РАЗМЫШЛЕНИЯМИ (enable_thinking=False)
            print("🔥 Прогрев модели (без размышлений)...")
            try:
                # Устанавливаем флаг прогрева чтобы избежать вывода
                if hasattr(model_service, '_warming_up'):
                    model_service._warming_up = True
                
                warmup_messages = [{"role": "user", "content": "Привет"}]
                warmup_response = model_service.generate_response(
                    warmup_messages, 
                    max_tokens=10,
                    temperature=0.1,
                    enable_thinking=False  # ← ВЫКЛЮЧАЕМ РАЗМЫШЛЕНИЯ
                )
                
                # Убираем флаг прогрева
                if hasattr(model_service, '_warming_up'):
                    model_service._warming_up = False
                
                # Не выводим ответ в консоль
                print("✅ Модель прогрета успешно")
                
            except Exception as e:
                print(f"ℹ️ Прогрев не удался: {e}, но модель загружена")
            
            return True
        else:
            print("❌ Не удалось загрузить модель")
            return False
            
    except Exception as e:
        print(f"❌ Критическая ошибка при загрузке модели: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("🚀 ЗАПУСК QWEN3-4B CHAT")
    print("=" * 60)
    
    # Регистрируем функцию очистки при выходе
    atexit.register(cleanup_on_exit)
    
    # Загружаем конфигурация
    print("\n⚙️  ЗАГРУЗКА КОНФИГУРАЦИИ...")
    try:
        config = container.get_config()
        print(f"✅ Конфигурация загружена:")
        print(f"   Приложение: {config.app.name} v{config.app.version}")
        print(f"   Модель: {config.model.name}")
        print(f"   Сервер: {config.server.host}:{config.server.port}")
        print(f"   Параметры: {config.generation.default_max_tokens} токенов, температура {config.generation.default_temperature}")
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
    
    # Инициализируем модель ОДИН РАЗ при старте
    print("\n🤖 ЗАГРУЗКА ИСКУССТВЕННОГО ИНТЕЛЛЕКТА...")
    model_loaded = initialize_model()
    
    if not model_loaded:
        print("\n⚠️  ВНИМАНИЕ: Модель не была загружена!")
        print("Приложение будет работать в режиме ожидания.")
        print("Модель попытается загрузиться при первом запросе.")
    
    # Создаем интерфейс
    print("\n🖥️  СОЗДАНИЕ ИНТЕРФЕЙСА...")
    try:
        demo, css_content = create_main_ui()
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
    print("\n📍 Ссылка для доступа:")
    print(f"   Локально: http://{config.server.host}:{config.server.port}")
    print(f"   В сети: {'Да' if config.server.share else 'Нет'}")
    
    if model_loaded:
        print("\n⚡ Модель в памяти - готово к работе!")
    else:
        print("\n⚠️  Модель не загружена - будет загружена при первом запросе")
    
    try:
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
            css=css_content
        )
    except Exception as e:
        print(f"❌ Ошибка запуска сервера: {e}")
        print("\n🔧 Возможные решения:")
        print(f"1. Проверьте, что порт {config.server.port} свободен")
        print("2. Попробуйте другой порт в config/app_config.yaml")
        print("3. Проверьте доступ к интернету (для загрузки модели)")

if __name__ == "__main__":
    main()