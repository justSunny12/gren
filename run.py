# /run.py (обновленные функции)

def print_memory_stats(prefix: str = ""):
    """Выводит статистику памяти для MLX"""
    try:
        import psutil
        
        process = psutil.Process()
        memory_info = process.memory_info()
        
        ram_used = memory_info.rss / 1024**3
        ram_percent = process.memory_percent()
        
        print(f"{prefix}💾 RAM: {ram_used:.2f} GB ({ram_percent:.1f}%)")
        
        # Для MLX показываем информацию о VRAM через Activity Monitor
        print(f"{prefix}🎮 MLX: Apple Silicon (общая память)")
        
    except Exception as e:
        print(f"{prefix}⚠️ Не удалось получить статистику памяти: {e}")

def initialize_model():
    """Инициализирует модель один раз при старте через MLX"""
    print("\n" + "-" * 50)
    print("📦 ИНИЦИАЛИЗАЦИЯ МОДЕЛИ (MLX)")
    print("-" * 50)
    
    try:
        # Получаем сервис модели
        model_service = container.get_model_service()
        
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
        
        # Загружаем модель через MLX
        start_time = time.time()
        model, tokenizer, lock = model_service.initialize()
        load_time = time.time() - start_time
        
        if model is not None:
            print(f"✅ Модель загружена через MLX за {load_time:.2f} секунд")
            
            # MLX автоматически использует GPU/Neural Engine
            print("⚡ Модель оптимизирована для Apple Silicon")
            
            return True
        else:
            print("❌ Не удалось загрузить модель через MLX")
            return False
            
    except Exception as e:
        print(f"❌ Критическая ошибка при загрузке модели через MLX: {e}")
        import traceback
        traceback.print_exc()
        return False