# /utils/memory_monitor.py
import psutil
import torch
import time
from typing import Dict, Any

class MemoryMonitor:
    """Монитор использования памяти"""
    
    @staticmethod
    def get_memory_usage() -> Dict[str, Any]:
        """Возвращает информацию об использовании памяти"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        result = {
            'ram_used_gb': memory_info.rss / 1024**3,
            'ram_percent': process.memory_percent(),
        }
        
        # GPU память (если есть CUDA)
        if torch.cuda.is_available():
            result.update({
                'gpu_used_gb': torch.cuda.memory_allocated() / 1024**3,
                'gpu_cached_gb': torch.cuda.memory_reserved() / 1024**3,
                'gpu_max_used_gb': torch.cuda.max_memory_allocated() / 1024**3,
            })
        
        # MPS память
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            result['device'] = 'mps'
        
        return result
    
    @staticmethod
    def print_memory_stats(prefix: str = ""):
        """Выводит статистику памяти"""
        stats = MemoryMonitor.get_memory_usage()
        
        print(f"{prefix}💾 RAM: {stats['ram_used_gb']:.2f} GB ({stats['ram_percent']:.1f}%)")
        
        if 'gpu_used_gb' in stats:
            print(f"{prefix}🎮 GPU: {stats['gpu_used_gb']:.2f} GB / кэш: {stats['gpu_cached_gb']:.2f} GB")