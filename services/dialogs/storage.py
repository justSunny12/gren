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
        datetime_str = dialog.created.strftime("%Y%m%dT%H%M%S")
        microseconds = dialog.created.strftime("%f")[:3]
        return f"{datetime_str}-{microseconds}"

    def _get_chat_folder_name(self, dialog: Dialog) -> str:
        return f"chat_{self._get_timestamp_suffix(dialog)}"

    def _get_chat_folder_path(self, dialog: Dialog) -> str:
        return os.path.join(self.save_dir, self._get_chat_folder_name(dialog))

    def _get_meta_file_path(self, dialog: Dialog) -> str:
        folder = self._get_chat_folder_path(dialog)
        return os.path.join(folder, f"meta_{self._get_timestamp_suffix(dialog)}.json")

    def _get_history_file_path(self, dialog: Dialog) -> str:
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

            history_file = self._get_history_file_path(dialog)
            if not os.path.exists(history_file):
                open(history_file, 'w', encoding='utf-8').close()

            return True

        except Exception as e:
            self.logger.error("Ошибка сохранения метаданных диалога %s: %s", dialog.id, e)
            return False

    # ========== Добавление сообщения (append) ==========

    def append_message(self, dialog: Dialog, message: Message) -> bool:
        """
        Добавляет одно сообщение в history_*.jsonl (append) и обновляет updated в meta.json.
        """
        try:
            history_file = self._get_history_file_path(dialog)
            if not os.path.exists(history_file):
                self.save_dialog(dialog)

            with open(history_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(message.to_dict(), ensure_ascii=False) + '\n')

            meta_file = self._get_meta_file_path(dialog)
            if os.path.exists(meta_file):
                with open(meta_file, 'r+', encoding='utf-8') as f:
                    meta = json.load(f)
                    meta['updated'] = dialog.updated.isoformat()
                    f.seek(0)
                    json.dump(meta, f, ensure_ascii=False, indent=2)
                    f.truncate()
            else:
                self.save_dialog(dialog)

            return True

        except Exception as e:
            self.logger.error("Ошибка добавления сообщения в диалог %s: %s", dialog.id, e)
            return False

    # ========== Перезапись последнего сообщения ==========

    def rewrite_last_message(self, dialog: Dialog) -> bool:
        """
        Перезаписывает последнюю строку history_*.jsonl актуальным содержимым
        последнего сообщения из dialog.history.

        Используется когда контент последнего сообщения изменён в памяти
        (например, нормализация блока размышлений) и нужно сохранить изменения.
        """
        if not dialog.history:
            return False

        try:
            history_file = self._get_history_file_path(dialog)
            if not os.path.exists(history_file):
                return False

            with open(history_file, 'rb') as f:
                # Ищем начало последней непустой строки
                f.seek(0, 2)
                file_size = f.tell()
                if file_size == 0:
                    return False

                # Шагаем назад побайтово, пропуская завершающий \n
                pos = file_size - 1
                f.seek(pos)
                if f.read(1) == b'\n':
                    pos -= 1

                # Находим начало последней строки
                while pos > 0:
                    f.seek(pos - 1)
                    if f.read(1) == b'\n':
                        break
                    pos -= 1
                last_line_start = pos

            # Перезаписываем файл: всё до последней строки + новая последняя строка
            with open(history_file, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = [l for l in content.splitlines() if l.strip()]
            if not lines:
                return False

            new_last = json.dumps(dialog.history[-1].to_dict(), ensure_ascii=False)
            lines[-1] = new_last

            with open(history_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')

            return True

        except Exception as e:
            self.logger.error("Ошибка перезаписи последнего сообщения диалога %s: %s", dialog.id, e)
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

                meta_files = [f for f in os.listdir(folder_path)
                              if f.startswith('meta_') and f.endswith('.json')]
                if not meta_files:
                    self.logger.warning("Пропуск папки %s: нет meta_*.json", folder_name)
                    continue

                meta_file = os.path.join(folder_path, meta_files[0])

                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                except Exception as e:
                    self.logger.error("Ошибка чтения %s в %s: %s", meta_files[0], folder_name, e)
                    continue

                dialog = Dialog(
                    id=meta["id"],
                    name=meta["name"],
                    created=datetime.fromisoformat(meta["created"]),
                    updated=datetime.fromisoformat(meta["updated"]),
                    status=meta.get("status", "active"),
                    pinned=meta.get("pinned", False),
                    pinned_position=meta.get("pinned_position"),
                )

                history_files = [f for f in os.listdir(folder_path)
                                 if f.startswith('history_') and f.endswith('.jsonl')]
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
                                    dialog.history.append(Message(**msg_data))
                                except Exception as e:
                                    self.logger.error("Ошибка парсинга сообщения в %s: %s",
                                                      history_file, e)

                dialogs[dialog.id] = dialog

        except Exception as e:
            self.logger.error("Критическая ошибка при загрузке диалогов: %s", e)

        return dialogs

    # ========== Удаление папки диалога ==========

    def delete_dialog_folder(self, dialog: Dialog) -> bool:
        try:
            folder_path = self._get_chat_folder_path(dialog)
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
                return True
            return False
        except Exception as e:
            self.logger.error("Ошибка удаления папки диалога %s: %s", dialog.id, e)
            return False