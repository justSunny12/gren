# /models/user_config_models.py
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
import copy

class UserGenerationConfig(BaseModel):
    max_tokens: Optional[int] = Field(None, ge=1, le=4096)
    temperature: Optional[float] = Field(None, ge=0.1, le=2.0)
    enable_thinking: Optional[bool] = None
    
    class Config:
        extra = "forbid"
    
    def to_dict(self) -> dict:
        data = {}
        if self.max_tokens is not None:
            data["max_tokens"] = self.max_tokens
        if self.temperature is not None:
            data["temperature"] = self.temperature
        if self.enable_thinking is not None:
            data["enable_thinking"] = self.enable_thinking
        return data


class UserConfig(BaseModel):
    generation: UserGenerationConfig = Field(default_factory=UserGenerationConfig)
    search_enabled: Optional[bool] = None  # новое поле
    
    class Config:
        extra = "forbid"
    
    def merge_with_defaults(self, default_config: Dict[str, Any]) -> Dict[str, Any]:
        result = copy.deepcopy(default_config)
        
        if self.generation.max_tokens is not None:
            result.setdefault("generation", {})["default_max_tokens"] = self.generation.max_tokens
        if self.generation.temperature is not None:
            result.setdefault("generation", {})["default_temperature"] = self.generation.temperature
        if self.generation.enable_thinking is not None:
            result.setdefault("generation", {})["default_enable_thinking"] = self.generation.enable_thinking
        
        # search_enabled не влияет на дефолтный конфиг, но может использоваться в других местах
        return result
    
    def to_dict(self) -> dict:
        data = {}
        gen_data = self.generation.to_dict()
        if gen_data:
            data["generation"] = gen_data
        if self.search_enabled is not None:
            data["search_enabled"] = self.search_enabled
        return data