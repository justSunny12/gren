# /models/user_config_models.py
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
import copy

class UserGenerationConfig(BaseModel):
    """Пользовательские настройки генерации"""
    max_tokens: Optional[int] = Field(None, ge=1, le=4096)
    temperature: Optional[float] = Field(None, ge=0.1, le=2.0)
    enable_thinking: Optional[bool] = None
    
    class Config:
        extra = "forbid"


class UserConfig(BaseModel):
    """Полная пользовательская конфигурация"""
    generation: UserGenerationConfig = Field(default_factory=UserGenerationConfig)
    
    class Config:
        extra = "forbid"
    
    def merge_with_defaults(self, default_config: Dict[str, Any]) -> Dict[str, Any]:
        """Объединяет пользовательские настройки со стандартными"""
        result = copy.deepcopy(default_config)
        
        # Объединяем настройки генерации
        if self.generation.max_tokens is not None:
            result.setdefault("generation", {})["default_max_tokens"] = self.generation.max_tokens
        
        if self.generation.temperature is not None:
            result.setdefault("generation", {})["default_temperature"] = self.generation.temperature
        
        if self.generation.enable_thinking is not None:
            result.setdefault("generation", {})["default_enable_thinking"] = self.generation.enable_thinking
        
        return result
    
    def to_dict(self) -> dict:
        """Конвертирует в словарь для сохранения"""
        data = {}
        
        # Добавляем только заданные пользователем значения
        gen_data = {}
        if self.generation.max_tokens is not None:
            gen_data["max_tokens"] = self.generation.max_tokens
        if self.generation.temperature is not None:
            gen_data["temperature"] = self.generation.temperature
        if self.generation.enable_thinking is not None:
            gen_data["enable_thinking"] = self.generation.enable_thinking
        
        if gen_data:
            data["generation"] = gen_data
        
        return data