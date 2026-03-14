# services/dialogs/storage.py
"""
Работа с файловой системой (загрузка/сохранение диалогов) с новой структурой:
- каждая папка chat_YYYYMMDDTHHMMSS-fff/
  - meta_YYYYMMDDTHHMMSS-fff.json          # метаданные (без истории)
  - history_YYYYMMDDTHHMMSS-fff.jsonl      # история в формате JSON lines
  - (опционально) context_YYYYMMDDTHHMMSS-fff.chat   # состояние контекста
"""
import os
import json
import shutil
from datetime import datetime
from typing import Dict, Optional

from models.dialog import Dialog
from models.enums import MessageRole
from models.message import Message
from container import container


class DialogStorage:
    """Управление сохранением и загрузкой диалогов с новой структурой файлов"""

    def __init__(self, config: dict):
        self.save_dir = config.get("save_dir", "saved_dialogs")
        os.makedirs(self.save_dir, exist_ok=True)
        self._logger = None

    @property
    def logger(self):
        if self._logger is None:
            self._logger = container.get_logger()
        return self._logger

    def _get_timestamp_suffix(self, dialog: Dialog) -> str:
        """Возвращает суффикс для файлов: YYYYMMDDTHHMMSS-fff"""
        datetime_str = dialog.created.strftime("%Y%m%dT%H%M%S")
        microseconds = dialog.created.strftime("%f")[:3]
        return f"{datetime_str}-{microseconds}"

    def _get_chat_folder_name(self, dialog: Dialog) -> str:
        """Имя папки: chat_<timestamp>-<micro>"""
        return f"chat_{self._get_timestamp_suffix(dialog)}"

    def _get_chat_folder_path(self, dialog: Dialog) -> str:
        return os.path.join(self.save_dir, self._get_chat_folder_name(dialog))

    def _get_meta_file_path(self, dialog: Dialog) -> str:
        """Путь к meta_<timestamp>-<micro>.json"""
        folder = self._get_chat_folder_path(dialog)
        return os.path.join(folder, f"meta_{self._get_timestamp_suffix(dialog)}.json")

    def _get_history_file_path(self, dialog: Dialog) -> str:
        """Путь к history_<timestamp>-<micro>.jsonl"""
        folder = self._get_chat_folder_path(dialog)
        return os.path.join(folder, f"history_{self._get_timestamp_suffix(dialog)}.jsonl")

    # ========== Сохранение метаданных ==========

    def save_dialog(self, dialog: Dialog) -> bool:
        """
        Сохраняет метаданные диалога в meta_*.json.
        Если папка ещё не существует – создаёт её и пустой history_*.jsonl.
        """
        try:
            folder_path = self._get_chat_folder_path(dialog)
            os.makedirs(folder_path, exist_ok=True)

            # Сохраняем метаданные (без истории)
            meta_file = self._get_meta_file_path(dialog)
            meta_data = {
                "id": dialog.id,
                "name": dialog.name,
                "created": dialog.created.isoformat(),
                "updated": dialog.updated.isoformat(),
                "status": dialog.status,
                "pinned": dialog.pinned,
                "pinned_position": dialog.pinned_position,
            }

            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, ensure_ascii=False, indent=2)

            # Если файл истории ещё не существует – создаём пустой
            history_file = self._get_history_file_path(dialog)
            if not os.path.exists(history_file):
                with open(history_file, 'w', encoding='utf-8') as f:
                    pass  # пустой файл

            return True

        except Exception as e:
            self.logger.error("Ошибка сохранения метаданных диалога %s: %s", dialog.id, e)
            return False

    # ========== Добавление сообщения (append) с обновлением только updated ==========

    def append_message(self, dialog: Dialog, message: Message) -> bool:
        """
        Добавляет одно сообщение в history_*.jsonl (append) и обновляет поле updated в meta.json.
        Предполагается, что message уже добавлено в dialog.history.
        """
        try:
            history_file = self._get_history_file_path(dialog)
            if not os.path.exists(history_file):
                # Если файла нет – создаём папку и файлы через save_dialog
                self.save_dialog(dialog)

            # Дописываем строку с сообщением
            with open(history_file, 'a', encoding='utf-8') as f:
                line = json.dumps(message.to_dict(), ensure_ascii=False) + '\n'
                f.write(line)

            # Обновляем только поле updated в meta.json (без полной перезаписи)
            meta_file = self._get_meta_file_path(dialog)
            if os.path.exists(meta_file):
                with open(meta_file, 'r+', encoding='utf-8') as f:
                    meta = json.load(f)
                    meta['updated'] = dialog.updated.isoformat()
                    f.seek(0)
                    json.dump(meta, f, ensure_ascii=False, indent=2)
                    f.truncate()
            else:
                # Если по какой-то причине meta отсутствует (например, удалён вручную), пересоздаём
                self.save_dialog(dialog)

            return True

        except Exception as e:
            self.logger.error("Ошибка добавления сообщения в диалог %s: %s", dialog.id, e)
            return False

    # ========== Загрузка всех диалогов ==========

    def load_dialogs(self) -> Dict[str, Dialog]:
        """Загружает все диалоги из папок chat_*"""
        dialogs = {}

        try:
            if not os.path.exists(self.save_dir):
                self.logger.info("Директория сохранённых диалогов не существует: %s", self.save_dir)
                return dialogs

            for folder_name in os.listdir(self.save_dir):
                folder_path = os.path.join(self.save_dir, folder_name)
                if not os.path.isdir(folder_path) or not folder_name.startswith('chat_'):
                    continue

                # Ищем файл meta_*.json (их может быть несколько, но должен быть один)
                meta_files = [f for f in os.listdir(folder_path) if f.startswith('meta_') and f.endswith('.json')]
                if not meta_files:
                    self.logger.warning("Пропуск папки %s: нет meta_*.json", folder_name)
                    continue

                # Берём первый (предполагаем, что он один)
                meta_file = os.path.join(folder_path, meta_files[0])

                # Загружаем метаданные
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                except Exception as e:
                    self.logger.error("Ошибка чтения %s в %s: %s", meta_files[0], folder_name, e)
                    continue

                # Создаём объект Dialog (без истории)
                dialog = Dialog(
                    id=meta["id"],
                    name=meta["name"],
                    created=datetime.fromisoformat(meta["created"]),
                    updated=datetime.fromisoformat(meta["updated"]),
                    status=meta.get("status", "active"),
                    pinned=meta.get("pinned", False),
                    pinned_position=meta.get("pinned_position"),
                )

                # Загружаем историю из history_*.jsonl (если есть)
                history_files = [f for f in os.listdir(folder_path) if f.startswith('history_') and f.endswith('.jsonl')]
                if history_files:
                    history_file = os.path.join(folder_path, history_files[0])
                    if os.path.exists(history_file):
                        with open(history_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if not line:
                                    continue
                                try:
                                    msg_data = json.loads(line)
                                    msg_data["role"] = MessageRole(msg_data["role"])
                                    msg_data["timestamp"] = datetime.fromisoformat(msg_data["timestamp"])
                                    message = Message(**msg_data)
                                    dialog.history.append(message)
                                except Exception as e:
                                    self.logger.error("Ошибка парсинга сообщения в %s: %s", history_file, e)
                                    continue

                dialogs[dialog.id] = dialog

        except Exception as e:
            self.logger.error("Критическая ошибка при загрузке диалогов: %s", e)

        return dialogs

    # ========== Удаление папки диалога ==========

    def delete_dialog_folder(self, dialog: Dialog) -> bool:
        """Удаляет папку диалога и всё её содержимое"""
        try:
            folder_path = self._get_chat_folder_path(dialog)
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
                return True
            return False
        except Exception as e:
            self.logger.error("Ошибка удаления папки диалога %s: %s", dialog.id, e)
            return False