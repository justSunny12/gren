# test_model_load.py
import time
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def test_direct_load():
    """Прямая загрузка модели"""
    print("🔍 Тест прямой загрузки модели...")
    
    model_name = "Qwen/Qwen3-4B"
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Устройство: {device}")
    
    # 1. Токенизатор
    start = time.time()
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    tokenizer_time = time.time() - start
    print(f"Токенизатор: {tokenizer_time:.2f} сек")
    
    # 2. Модель с разными параметрами
    test_cases = [
        {"low_cpu_mem_usage": False, "torch_dtype": torch.float32},
        {"low_cpu_mem_usage": True, "torch_dtype": torch.float32},
        {"low_cpu_mem_usage": True, "torch_dtype": torch.float16},
    ]
    
    for i, params in enumerate(test_cases):
        print(f"\nТест {i+1}: {params}")
        try:
            start = time.time()
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                trust_remote_code=True,
                **params
            )
            
            if device == "mps":
                model = model.to("mps")
            
            load_time = time.time() - start
            print(f"  Загрузка: {load_time:.2f} сек")
            print(f"  Параметры: {sum(p.numel() for p in model.parameters()):,}")
            
            # Очистка
            del model
            torch.mps.empty_cache() if device == "mps" else torch.cuda.empty_cache()
            
        except Exception as e:
            print(f"  Ошибка: {e}")

if __name__ == "__main__":
    test_direct_load()