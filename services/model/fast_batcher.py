"""
Умный батчер с минимальным оверхедом на корутинах
Оптимизирован для ~50 токенов/секунду
"""
import time
from typing import List
from dataclasses import dataclass
from threading import Lock

@dataclass
class BatchConfig:
    """Конфигурация батчера для оптимального UX"""
    # Оптимальные параметры для 50 токенов/сек
    min_chars_per_batch: int = 6      # ~1.5 токена (минимальная порция для "печатания")
    target_chars_per_batch: int = 16  # ~4 токена (целевой размер батча)
    max_chars_per_batch: int = 24     # ~6 токенов (максимум перед срочной отправкой)
    
    # Тайминги (миллисекунды)
    min_batch_wait_ms: float = 20.0   # Минимальная задержка между батчами
    max_batch_wait_ms: float = 60.0   # Максимальная задержка (незаметно для глаза)
    
    # Адаптивные настройки
    adaptive_mode: bool = True        # Автоподстройка под скорость
    speed_history_size: int = 5       # Размер истории для расчета скорости


class FastBatcher:
    """
    Асинхронный батчер, который не блокирует генерацию.
    Использует механизм условных переменных для минимального оверхед.
    """
    
    def __init__(self, config: BatchConfig = None):
        self.config = config or BatchConfig()
        self._lock = Lock()
        self._buffer: List[str] = []
        self._buffer_size = 0
        self._stop_requested = False
        self._last_flush_time = time.time()
        self._speed_history = []
        self._total_chars = 0
        self._start_time = None
        
    def start(self):
        """Инициализация батчера (синхронная)"""
        self._start_time = time.time()
    
    def stop(self):
        """Остановка батчера"""
        with self._lock:
            self._stop_requested = True
    
    def is_stopped(self) -> bool:
        """Проверка остановки"""
        with self._lock:
            return self._stop_requested
    
    def put(self, chunk: str) -> bool:
        """
        Добавляет чанк в буфер.
        Возвращает True, если нужно отправить батч.
        """
        if not chunk:
            return False
        
        with self._lock:
            if self._stop_requested:
                return False
            
            # Добавляем чанк
            self._buffer.append(chunk)
            self._buffer_size += len(chunk)
            
            # Обновляем статистику скорости
            self._total_chars += len(chunk)
            
            # Вычисляем текущие параметры
            current_time = time.time()
            time_since_flush = (current_time - self._last_flush_time) * 1000
            
            # Адаптивная подстройка
            if self.config.adaptive_mode and self._start_time:
                elapsed = current_time - self._start_time
                if elapsed > 0.5:  # Раз в 0.5 секунды пересчитываем
                    speed = self._total_chars / elapsed
                    self._update_speed_history(speed)
                    self._adjust_config()
            
            # Принятие решения о флаше
            should_flush = False
            
            # 1. Срочный flush: слишком много накопилось
            if self._buffer_size >= self.config.max_chars_per_batch:
                should_flush = True
            
            # 2. Обычный flush: достигли целевого размера + прошло минимальное время
            elif (self._buffer_size >= self.config.target_chars_per_batch and 
                  time_since_flush >= self.config.min_batch_wait_ms):
                should_flush = True
            
            # 3. Вынужденный flush: прошло слишком много времени
            elif time_since_flush >= self.config.max_batch_wait_ms:
                should_flush = True
            
            # 4. Микро-flush: очень короткий чанк после небольшой паузы
            elif (len(chunk) <= 2 and  # Очень короткий чанк (знаки препинания)
                  time_since_flush >= 30 and  # Прошло 30мс
                  self._buffer_size >= self.config.min_chars_per_batch):
                should_flush = True
            
            if should_flush:
                self._last_flush_time = current_time
            
            return should_flush
    
    def take_batch(self) -> str:
        """
        Извлекает собранный батч из буфера.
        Должен вызываться после put() вернувшего True.
        """
        with self._lock:
            if not self._buffer:
                return ""
            
            batch = ''.join(self._buffer)
            self._buffer = []
            self._buffer_size = 0
            return batch
    
    def get_current_batch(self) -> str:
        """Получает текущий батч без очистки (для отладки)"""
        with self._lock:
            return ''.join(self._buffer) if self._buffer else ""
    
    def _update_speed_history(self, current_speed: float):
        """Обновляет историю скорости"""
        self._speed_history.append(current_speed)
        if len(self._speed_history) > self.config.speed_history_size:
            self._speed_history.pop(0)
    
    def _adjust_config(self):
        """Адаптивно подстраивает параметры под скорость"""
        if len(self._speed_history) < 3:
            return
        
        avg_speed = sum(self._speed_history) / len(self._speed_history)
        
        # Нормализуем скорость (предполагаем 20-80 токенов/сек = 80-320 символов/сек)
        norm_speed = min(1.0, max(0.0, (avg_speed - 80) / (320 - 80)))
        
        # Адаптируем размеры батчей
        base_min = 6
        base_target = 16
        base_max = 24
        
        # При высокой скорости увеличиваем батчи, при низкой - уменьшаем
        self.config.min_chars_per_batch = int(base_min + norm_speed * 4)
        self.config.target_chars_per_batch = int(base_target + norm_speed * 8)
        self.config.max_chars_per_batch = int(base_max + norm_speed * 12)
        
        # Адаптируем тайминги
        self.config.min_batch_wait_ms = max(15.0, 30.0 - norm_speed * 15.0)
        self.config.max_batch_wait_ms = max(40.0, 80.0 - norm_speed * 30.0)