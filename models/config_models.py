# /models/config_models.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum

class ModelDtype(str, Enum):
    AUTO = "auto"
    FLOAT16 = "float16"
    BFLOAT16 = "bfloat16"

class AppConfig(BaseModel):
    """Конфигурация приложения"""
    name: str = "Qwen3-4B Chat"
    version: str = "1.0.0"
    debug: bool = False
    theme: str = "soft"

class ServerConfig(BaseModel):
    """Конфигурация сервера"""
    host: str = "0.0.0.0"
    port: int = 7860
    share: bool = False
    show_error: bool = True

class QueueConfig(BaseModel):
    """Конфигурация очереди"""
    max_size: int = 5
    concurrency_limit: int = 1

class DialogConfig(BaseModel):
    """Конфигурация диалогов"""
    save_dir: str = "saved_dialogs"
    default_name: str = "Новый чат"

class ModelConfig(BaseModel):
    """Конфигурация модели"""
    name: str = "Qwen/Qwen3-4B"
    dtype: ModelDtype = ModelDtype.BFLOAT16
    attn_implementation: str = "eager"
    low_cpu_mem_usage: bool = True

class GenerationConfig(BaseModel):
    """Конфигурация генерации"""
    default_max_tokens: int = Field(512, ge=1, le=4096)
    default_temperature: float = Field(0.7, ge=0.1, le=2.0)
    default_top_p: float = Field(0.9, ge=0.0, le=1.0)
    default_repetition_penalty: float = Field(1.1, ge=1.0, le=2.0)
    
    min_max_tokens: int = 64
    max_max_tokens: int = 2048
    min_temperature: float = 0.1
    max_temperature: float = 1.5

class ChatNamingConfig(BaseModel):
    """Конфигурация генерации названий чатов"""
    max_name_length: int = 50
    summary_max_tokens: int = 20
    summary_temperature: float = 0.4

class UIConfig(BaseModel):
    """Конфигурация UI"""
    class SidebarConfig(BaseModel):
        width: str = "300px"
        min_width: str = "300px"
        max_width: str = "350px"
        background: str = "#f8f9fa"
        border_color: str = "#e0e0e0"
    
    class ChatWindowConfig(BaseModel):
        background: str = "white"
        border_color: str = "#e0e0e0"
        border_radius: str = "8px"
        padding: str = "12px"
    
    class InputAreaConfig(BaseModel):
        height: str = "110px"
        min_height: str = "110px"
        max_height: str = "110px"
        background: str = "white"
        border_color: str = "#e0e0e0"
        border_radius: str = "6px"
    
    class ButtonsConfig(BaseModel):
        primary_color: str = "#007bff"
        primary_hover: str = "#0056b3"
        secondary_color: str = "#6c757d"
        danger_color: str = "#dc3545"
    
    class TextConfig(BaseModel):
        font_family: str = "inherit"
        font_size: str = "14px"
        line_height: str = "1.4"
    
    class MessagesConfig(BaseModel):
        user_bg: str = "#e3f2fd"
        user_border: str = "#bbdefb"
        bot_bg: str = "#f5f5f5"
        bot_border: str = "#e0e0e0"
        max_width: str = "75%"
        border_radius: str = "12px"
        padding: str = "10px 14px"
    
    sidebar: SidebarConfig = SidebarConfig()
    chat_window: ChatWindowConfig = ChatWindowConfig()
    input_area: InputAreaConfig = InputAreaConfig()
    buttons: ButtonsConfig = ButtonsConfig()
    text: TextConfig = TextConfig()
    messages: MessagesConfig = MessagesConfig()

class PathsConfig(BaseModel):
    """Конфигурация путей"""
    css_dir: str = "css"
    saved_dialogs: str = "saved_dialogs"
    logs: str = "logs"
    css_files: List[str] = Field(default_factory=list)
    
    @validator('css_files', pre=True, always=True)
    def set_css_files(cls, v):
        if not v:
            return [
                "css/base.css",
                "css/sidebar.css",
                "css/chat_window.css",
                "css/input_area.css"
            ]
        return v

class FullConfig(BaseModel):
    """Полная конфигурация приложения"""
    app: AppConfig = AppConfig()
    server: ServerConfig = ServerConfig()
    queue: QueueConfig = QueueConfig()
    dialogs: DialogConfig = DialogConfig()
    model: ModelConfig = ModelConfig()
    generation: GenerationConfig = GenerationConfig()
    chat_naming: ChatNamingConfig = ChatNamingConfig()
    ui: UIConfig = UIConfig()
    paths: PathsConfig = PathsConfig()