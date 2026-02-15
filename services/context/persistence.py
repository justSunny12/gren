# services/context/persistence.py
"""
Сохранение и загрузка состояния контекста.
"""
import os
import json
from typing import Optional

from models.dialog import Dialog
from models.context import DialogContextState


class ContextStatePersistence:
    """Управляет файловым хранилищем состояния контекста."""

    def __init__(self, dialog: Dialog, config: dict):
        self.dialog = dialog
        self.config = config

    def get_state_file_path(self) -> str:
        """Генерирует путь к файлу состояния контекста."""
        from container import container
        config_service = container.get("config_service")
        app_config = config_service.get_config()
        save_dir = app_config.get("dialogs", {}).get("save_dir", "saved_dialogs")

        datetime_str = self.dialog.created.strftime("%Y%m%dT%H%M%S")
        microseconds = self.dialog.created.strftime("%f")[:3]
        chat_folder = f"chat_{datetime_str}-{microseconds}"
        folder_path = os.path.join(save_dir, chat_folder)
        os.makedirs(folder_path, exist_ok=True)

        context_file = f"context_{datetime_str}-{microseconds}.chat"
        return os.path.join(folder_path, context_file)

    def save(self, state: DialogContextState, file_path: Optional[str] = None) -> bool:
        """Сохраняет состояние в файл."""
        if file_path is None:
            file_path = self.get_state_file_path()
        try:
            state_dict = state.model_dump_jsonable()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(state_dict, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения состояния контекста: {e}")
            return False

    def load(self, file_path: Optional[str] = None) -> Optional[DialogContextState]:
        """Загружает состояние из файла."""
        if file_path is None:
            file_path = self.get_state_file_path()
        try:
            if not os.path.exists(file_path):
                return None
            with open(file_path, 'r', encoding='utf-8') as f:
                state_dict = json.load(f)
            return DialogContextState.model_validate(state_dict)
        except Exception as e:
            print(f"❌ Ошибка загрузки состояния контекста: {e}")
            return None