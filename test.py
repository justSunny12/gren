#!/usr/bin/env python3
"""
Переносит модель из кэша HF в ./models/ с сохранением структуры
"""

import os
import sys
import shutil
import hashlib
from pathlib import Path

def find_hf_cache():
    """Находит кэш HF"""
    cache_paths = [
        Path.home() / ".cache" / "huggingface" / "hub",
        Path.home() / "Library" / "Caches" / "huggingface",
        Path.home() / ".cache" / "huggingface",
    ]
    
    for cache_path in cache_paths:
        if cache_path.exists():
            qwen_path = cache_path / "models--Qwen--Qwen3-30B-A3B-MLX-4bit"
            if qwen_path.exists():
                return qwen_path
    return None

def get_blobs_size(cache_path):
    """Рассчитывает размер blobs"""
    blobs_path = cache_path / "blobs"
    if not blobs_path.exists():
        return 0
    
    total_size = 0
    for blob_file in blobs_path.glob("*"):
        if blob_file.is_file():
            total_size += blob_file.stat().st_size
    return total_size

def copy_model(cache_path, target_dir):
    """Копирует всю структуру модели"""
    print(f"📦 Копирование модели...")
    print(f"   Из: {cache_path}")
    print(f"   В: {target_dir}")
    
    # Создаём целевую директорию
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Копируем ВСЕ содержимое кэша
    for item in cache_path.iterdir():
        src_path = cache_path / item.name
        dst_path = target_dir / item.name
        
        print(f"   📁 {item.name}: ", end="")
        
        if item.name == "blobs":
            # Для blobs показываем прогресс
            blobs_size = get_blobs_size(cache_path) / 1024**3
            print(f"{blobs_size:.1f} GB", flush=True)
            
            # Копируем blobs с прогрессом
            copy_blobs_with_progress(src_path, dst_path)
            
        elif item.is_dir():
            # Для директорий (snapshots, refs)
            shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            size_mb = sum(f.stat().st_size for f in src_path.rglob('*') if f.is_file()) / 1024**2
            print(f"{size_mb:.1f} MB")
        else:
            # Для файлов
            shutil.copy2(src_path, dst_path)
            size_kb = src_path.stat().st_size / 1024
            print(f"{size_kb:.1f} KB")
    
    return target_dir

def copy_blobs_with_progress(src_blobs, dst_blobs):
    """Копирует blobs с индикатором прогресса"""
    dst_blobs.mkdir(exist_ok=True)
    blobs = list(src_blobs.glob("*"))
    total = len(blobs)
    
    for i, blob in enumerate(blobs, 1):
        if blob.is_file():
            dst_file = dst_blobs / blob.name
            if not dst_file.exists():
                shutil.copy2(blob, dst_file)
            
            # Прогресс каждые 10% или 100 файлов
            if i % max(100, total//10) == 0 or i == total:
                sys.stdout.write(f"\r     [{i}/{total}] файлов скопировано")
                sys.stdout.flush()
    
    print()  # Новая строка после прогресса

def find_latest_snapshot(model_dir):
    """Находит последний snapshot"""
    snapshots_dir = model_dir / "snapshots"
    if not snapshots_dir.exists():
        return None
    
    snapshots = list(snapshots_dir.iterdir())
    if not snapshots:
        return None
    
    # Возвращаем первый snapshot (обычно он один)
    return snapshots[0]

def create_model_link(model_dir, snapshot_path):
    """Создаёт удобную ссылку на модель"""
    link_path = Path("./models/qwen3-30b-a3b-mlx")
    
    # Удаляем старую ссылку если есть
    if link_path.exists():
        if link_path.is_symlink():
            link_path.unlink()
        else:
            backup = Path(f"{link_path}.backup")
            shutil.move(link_path, backup)
            print(f"⚠️  Существующая папка переименована в: {backup}")
    
    # Создаём символическую ссылку
    link_path.symlink_to(snapshot_path, target_is_directory=True)
    return link_path

def main():
    print("=" * 60)
    print("🚀 ПЕРЕНОС МОДЕЛИ ИЗ КЭША В ./models/")
    print("=" * 60)
    
    # 1. Находим кэш
    cache_path = find_hf_cache()
    if not cache_path:
        print("❌ Модель не найдена в кэше HF")
        print("\n📥 Попробуйте скачать заново:")
        print("python -c \"from mlx_lm import load; load('Qwen/Qwen3-30B-A3B-MLX-4bit')\"")
        return
    
    print(f"✅ Найден кэш: {cache_path}")
    
    # 2. Показываем размер
    total_size = 0
    for item in cache_path.glob("**/*"):
        if item.is_file():
            total_size += item.stat().st_size
    
    print(f"📊 Общий размер: {total_size / 1024**3:.2f} GB")
    
    # 3. Подтверждение
    print(f"\n⚠️  Будет скопировано: {total_size / 1024**3:.1f} GB")
    response = input("   Продолжить? (y/n): ")
    if response.lower() != 'y':
        print("Отменено.")
        return
    
    # 4. Определяем путь назначения
    target_base = Path("./models/hf-cache")
    target_dir = target_base / "models--Qwen--Qwen3-30B-A3B-MLX-4bit"
    
    print(f"\n🎯 Целевой путь: {target_dir}")
    
    # 5. Копируем
    try:
        model_dir = copy_model(cache_path, target_dir)
        
        # 6. Находим snapshot
        snapshot_path = find_latest_snapshot(model_dir)
        if not snapshot_path:
            print("❌ Не удалось найти snapshot в скопированной модели")
            return
        
        print(f"\n✅ Модель успешно скопирована")
        print(f"📁 Snapshot: {snapshot_path}")
        
        # 7. Проверяем целостность
        print("\n🔍 Проверка целостности...")
        required_files = ["config.json", "tokenizer.json"]
        missing = []
        
        for req_file in required_files:
            if not (snapshot_path / req_file).exists():
                missing.append(req_file)
        
        if missing:
            print(f"⚠️  Отсутствуют файлы: {missing}")
        else:
            print("✅ Все ключевые файлы на месте")
        
        # 8. Создаём удобную ссылку
        print("\n🔗 Создание удобной ссылки...")
        link_path = create_model_link(model_dir, snapshot_path)
        print(f"✅ Создана ссылка: {link_path} -> {snapshot_path}")
        
        # 9. Показываем результат
        print("\n" + "=" * 60)
        print("🎉 ГОТОВО! Добавьте в config/model_config.yaml:")
        print("=" * 60)
        print(f"\n# Вариант 1: Прямой путь к snapshot")
        print(f"local_path: \"{snapshot_path}\"")
        print(f"\n# Вариант 2: Использовать симлинк (рекомендуется)")
        print(f"local_path: \"./models/qwen3-30b-a3b-mlx\"")
        print(f"\n# Вариант 3: Полный путь к кэшу")
        print(f"local_path: \"{model_dir}\"")
        
        # 10. Проверка размера snapshot
        snapshot_size = sum(f.stat().st_size for f in snapshot_path.rglob('*') if f.is_file()) / 1024**2
        print(f"\n📊 Snapshot (симлинки): {snapshot_size:.1f} MB")
        print(f"📊 Полный кэш: {total_size / 1024**3:.1f} GB")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    main()