"""
Управление памятью MLX
"""
import mlx.core as mx

class MLXMemoryManager:
    """Менеджер памяти для MLX"""
    
    def setup_memory_limit(self, model_config: dict) -> bool:
        """Устанавливает лимит памяти для MLX"""
        memory_limit = model_config.get("unified_memory_limit")
        
        if memory_limit and hasattr(mx.metal, 'set_cache_limit'):
            try:
                # Конвертируем проценты в байты
                total_memory = mx.device_info().get('memory_size', 0)
                if not total_memory:
                    print("⚠️ Не удалось определить общий объем памяти")
                    return False
                
                limit_bytes = int(total_memory * (memory_limit / 100))
                mx.set_cache_limit(limit_bytes)
                print(f"🛠️  Установлен лимит памяти MLX: {limit_bytes/1024**3:.2f} GB\n")
                return True
            except Exception as e:
                print(f"⚠️ Не удалось установить лимит памяти: {e}")
                return False
        
        return False