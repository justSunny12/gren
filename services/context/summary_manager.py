# services/context/summary_manager.py
"""
Менеджер для координации фоновых суммаризаций с реальными моделями
"""
import asyncio
import threading
import time
from typing import List, Dict, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import queue
from functools import total_ordering

from services.context.summarizers import SummarizerFactory, SummaryResult


@total_ordering
@dataclass
class SummaryTask:
    """Задача суммаризации (сравнимый для PriorityQueue)"""
    task_id: str
    task_type: str  # "l1" или "l2"
    data: Any  # Данные для суммаризации
    priority: int = 1  # Приоритет (1-10, где 10 - наивысший)
    created_at: float = field(default_factory=time.time)
    sequence_number: int = 0  # Порядковый номер для сравнения
    callback: Optional[Callable] = None
    extra_params: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """Сравнение для PriorityQueue: сначала приоритет, затем порядковый номер"""
        if not isinstance(other, SummaryTask):
            return NotImplemented
        
        # Сравниваем по приоритету (высший приоритет = меньшее число для heapq)
        if self.priority != other.priority:
            return self.priority > other.priority  # Более высокий приоритет = "меньше"
        
        # При равном приоритете сравниваем по порядковый номер (FIFO)
        return self.sequence_number < other.sequence_number
    
    def __eq__(self, other):
        if not isinstance(other, SummaryTask):
            return NotImplemented
        return (self.task_id == other.task_id and 
                self.priority == other.priority and
                self.sequence_number == other.sequence_number)


class SummaryManager:
    """Менеджер фоновых суммаризаций с реальными моделями"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Очередь задач с приоритетом
        self._task_queue = queue.PriorityQueue()  # Используем PriorityQueue для приоритетов
        self._running_tasks: Set[str] = set()
        self._completed_tasks: Dict[str, SummaryResult] = {}
        self._failed_tasks: Dict[str, str] = {}
        
        # Счетчик для порядка задач
        self._task_counter = 0
        self._task_counter_lock = threading.Lock()
        
        # Потоки и асинхронность
        self._executor = ThreadPoolExecutor(
            max_workers=config.get("performance", {}).get("max_background_tasks", 2),
            thread_name_prefix="SummaryWorker"
        )
        self._stop_event = threading.Event()
        self._worker_thread = None
        
        # Статистика
        self._total_tasks = 0
        self._successful_tasks = 0
        self._failed_tasks_count = 0
        self._total_processing_time = 0.0
        
        # Суммаризаторы (будут загружены лениво)
        self._summarizers = None
        
        # Блокировки
        self._lock = threading.RLock()
        
        # Задержка перед началом суммаризации
        self._summary_delay = config.get("performance", {}).get("summary_delay_ms", 1000) / 1000.0
    
    def _get_summarizers(self):
        """Ленивая инициализация суммаризаторов"""
        if self._summarizers is None:
            self._summarizers = SummarizerFactory.get_all_summarizers(self.config)
        return self._summarizers
    
    def _get_next_sequence_number(self) -> int:
        """Получает следующий порядковый номер для задачи"""
        with self._task_counter_lock:
            self._task_counter += 1
            return self._task_counter
    
    def schedule_l1_summary(self, text: str, callback: Optional[Callable] = None, 
                           priority: int = 1, **kwargs) -> str:
        """Планирует задачу L1 суммаризации"""
        task_id = f"l1_{int(time.time() * 1000)}_{hash(text) % 10000:04d}"
        
        task = SummaryTask(
            task_id=task_id,
            task_type="l1",
            data=text,
            priority=priority,
            callback=callback,
            sequence_number=self._get_next_sequence_number(),
            extra_params=kwargs
        )
        
        with self._lock:
            self._task_queue.put((-priority, task))
            self._total_tasks += 1
        
        return task_id
    
    def schedule_l2_summary(self, text: str, original_char_count: int, l1_chunk_ids: List[str], 
                           callback: Optional[Callable] = None,
                           priority: int = 5,
                           **kwargs) -> str:
        """Планирует задачу L2 суммаризации с дополнительными данными"""
        data = {
            "text": text,
            "original_char_count": original_char_count,
            "l1_chunk_ids": l1_chunk_ids
        }
        
        task_id = f"l2_{int(time.time() * 1000)}_{hash(str(l1_chunk_ids)) % 10000:04d}"
        
        task = SummaryTask(
            task_id=task_id,
            task_type="l2",
            data=data,
            priority=priority,
            callback=callback,
            sequence_number=self._get_next_sequence_number(),
            extra_params=kwargs
        )
        
        with self._lock:
            self._task_queue.put((-priority, task))
            self._total_tasks += 1
        
        return task_id
    
    def start(self):
        """Запускает менеджер суммаризаций"""
        if self._worker_thread is not None and self._worker_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name="SummaryManagerWorker",
            daemon=True
        )
        self._worker_thread.start()
        print("🚀 Менеджер суммаризаций запущен")
    
    def stop(self):
        """Останавливает менеджер суммаризаций"""
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
        self._executor.shutdown(wait=True)
        
        # Выгружаем модели
        if self._summarizers:
            SummarizerFactory.unload_all()
        
        print("🛑 Менеджер суммаризаций остановлен")
    
    def _worker_loop(self):
        """Основной цикл обработки задач"""
        print("👷 Воркер суммаризаций запущен")
        
        while not self._stop_event.is_set():
            try:
                # Получаем задачу из очереди с таймаутом
                try:
                    priority, task = self._task_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                # Проверяем, не выполняется ли уже задача с таким ID
                with self._lock:
                    if task.task_id in self._running_tasks:
                        # Пропускаем дубликат и отмечаем задачу как выполненную
                        self._task_queue.task_done()
                        continue
                    
                    self._running_tasks.add(task.task_id)
                
                # Выполняем задачу в пуле потоков
                future = self._executor.submit(self._execute_task, task)
                future.add_done_callback(lambda f: self._task_queue.task_done())
                
            except Exception as e:
                print(f"⚠️ Ошибка в воркере суммаризаций: {e}")
                import traceback
                traceback.print_exc()
        
        print("👷 Воркер суммаризаций остановлен")
    
    def _execute_task(self, task: SummaryTask):
        """Выполняет задачу суммаризации с реальной моделью"""
        start_time = time.time()
        
        try:
            # Добавляем задержку для накопления задач
            if time.time() - task.created_at < self._summary_delay:
                time.sleep(self._summary_delay)
            
            print(f"⚡ Выполняю задачу {task.task_id} (тип: {task.task_type})")
            
            # Получаем соответствующий суммаризатор
            summarizers = self._get_summarizers()
            
            if task.task_type == "l1":
                summarizer = summarizers["l1"]
                result = asyncio.run(summarizer.summarize(
                    task.data,
                    **task.extra_params
                ))
                    
            elif task.task_type == "l2":
                summarizer = summarizers["l2"]
                # Для L2 передаем текст и дополнительные данные
                text = task.data["text"]
                result = asyncio.run(summarizer.summarize(
                    text,
                    original_char_count=task.data["original_char_count"],
                    **task.extra_params
                ))
            else:
                raise ValueError(f"Неизвестный тип задачи: {task.task_type}")
            
            processing_time = time.time() - start_time
            
            with self._lock:
                if result.success:
                    self._successful_tasks += 1
                    self._completed_tasks[task.task_id] = result
                    print(f"✅ Задача {task.task_id} выполнена за {processing_time:.2f}с "
                          f"(сжатие: {result.compression_ratio:.1f}x)")
                else:
                    self._failed_tasks_count += 1
                    self._failed_tasks[task.task_id] = result.error
                    print(f"❌ Задача {task.task_id} провалена: {result.error}")
                
                self._total_processing_time += processing_time
                self._running_tasks.discard(task.task_id)
            
            # Вызываем callback если есть
            if task.callback and result.success:
                try:
                    if task.task_type == "l1":
                        # Для L1 передаем результат и исходный текст
                        task.callback(result.summary, task.data)
                    elif task.task_type == "l2":
                        # Для L2 передаем результат, исходный текст, l1_chunk_ids и original_char_count
                        task.callback(
                            result.summary, 
                            task.data["text"],
                            task.data["l1_chunk_ids"],
                            task.data["original_char_count"]
                        )
                except Exception as e:
                    print(f"⚠️ Ошибка в callback задачи {task.task_id}: {e}")
            
            return result
            
        except Exception as e:
            error_msg = f"Неожиданная ошибка в задаче {task.task_id}: {str(e)}"
            print(f"❌ {error_msg}")
            
            with self._lock:
                self._failed_tasks_count += 1
                self._failed_tasks[task.task_id] = error_msg
                self._running_tasks.discard(task.task_id)
            
            return SummaryResult(
                summary="",
                original_length=0,
                summary_length=0,
                compression_ratio=1.0,
                processing_time=time.time() - start_time,
                success=False,
                error=error_msg
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику менеджера"""
        with self._lock:
            summarizer_stats = SummarizerFactory.get_stats()
            
            return {
                "manager": {
                    "is_running": self._worker_thread is not None and self._worker_thread.is_alive(),
                    "total_tasks": self._total_tasks,
                    "successful_tasks": self._successful_tasks,
                    "failed_tasks": self._failed_tasks_count,
                    "success_rate": self._successful_tasks / max(self._total_tasks, 1),
                    "avg_processing_time": self._total_processing_time / max(self._successful_tasks, 1),
                    "queue_size": self._task_queue.qsize(),
                    "running_tasks": len(self._running_tasks),
                    "completed_tasks": len(self._completed_tasks),
                    "failed_tasks_dict": len(self._failed_tasks)
                },
                "summarizers": summarizer_stats
            }