"""
Скрипт для тестирования батчинга
"""
import asyncio
import time
from services.model.fast_batcher import FastBatcher, BatchConfig

async def test_batcher():
    """Тестирует работу батчера с разными скоростями"""
    
    print("🧪 Тестирование FastBatcher")
    print("=" * 50)
    
    # Тест 1: Быстрая генерация (имитация 50 токенов/сек)
    print("\n1. Быстрая генерация (~50 токенов/сек):")
    batcher = FastBatcher(BatchConfig(
        min_chars_per_batch=6,
        target_chars_per_batch=16,
        max_chars_per_batch=24,
        min_batch_wait_ms=20.0,
        max_batch_wait_ms=60.0,
        adaptive_mode=True
    ))
    batcher.start()
    
    # Имитируем быстрые чанки (токены)
    chunks = ["При", "вет", ",", " ", "ка", "к", " ", "де", "ла", "?", " "]
    
    start_time = time.time()
    batch_count = 0
    total_chars = 0
    
    for chunk in chunks:
        should_flush = batcher.put(chunk)
        total_chars += len(chunk)
        
        if should_flush:
            batch = batcher.take_batch()
            batch_count += 1
            print(f"  Батч {batch_count}: '{batch}' ({len(batch)} символов)")
        
        # Имитируем задержку генерации (~20мс на токен)
        await asyncio.sleep(0.02)
    
    # Оставшиеся данные
    final_batch = batcher.take_batch()
    if final_batch:
        batch_count += 1
        print(f"  Финальный батч: '{final_batch}' ({len(final_batch)} символов)")
    
    elapsed = time.time() - start_time
    print(f"  Итого: {batch_count} батчей за {elapsed:.2f} сек, {total_chars} символов")
    print(f"  Скорость: {total_chars/elapsed:.1f} символов/сек")
    
    # Тест 2: Медленная генерация
    print("\n2. Медленная генерация (~20 токенов/сек):")
    batcher2 = FastBatcher()
    batcher2.start()
    
    chunks_slow = ["Мед", "лен", "но", " ", "ге", "не", "ри", "ру", "ю"]
    
    start_time = time.time()
    batch_count = 0
    total_chars = 0
    
    for chunk in chunks_slow:
        should_flush = batcher2.put(chunk)
        total_chars += len(chunk)
        
        if should_flush:
            batch = batcher2.take_batch()
            batch_count += 1
            print(f"  Батч {batch_count}: '{batch}' ({len(batch)} символов)")
        
        # Медленная генерация (~50мс на токен)
        await asyncio.sleep(0.05)
    
    elapsed = time.time() - start_time
    print(f"  Итого: {batch_count} батчей за {elapsed:.2f} сек")
    print(f"  Скорость: {total_chars/elapsed:.1f} символов/сек")
    
    # Статистика адаптации
    print("\n3. Статистика адаптации:")
    stats = batcher.get_stats()
    print(f"  Средняя скорость: {stats['avg_speed']:.1f} символов/сек")
    print(f"  Адаптированные параметры:")
    print(f"    - min_chars: {stats['config']['min_chars']}")
    print(f"    - target_chars: {stats['config']['target_chars']}")
    print(f"    - max_chars: {stats['config']['max_chars']}")
    
    print("\n✅ Тестирование завершено")

if __name__ == "__main__":
    asyncio.run(test_batcher())