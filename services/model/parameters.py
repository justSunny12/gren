"""
Управление параметрами генерации - ВСЕ параметры независимы
"""
from typing import Dict, Any, Optional


class GenerationParameters:
    """Управление параметрами генерации"""
    
    def __init__(self, config: dict):
        self.config = config
    
    def get_generation_parameters(
        self,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        enable_thinking: Optional[bool] = None,
        top_p: Optional[float] = None,        # ← Добавляем поддержку top_p из UI
        top_k: Optional[int] = None,          # ← Добавляем поддержку top_k из UI
        repetition_penalty: Optional[float] = None  # ← Добавляем поддержку repetition_penalty
    ) -> Dict[str, Any]:
        """Определяет итоговые параметры генерации"""
        
        # enable_thinking НЕ влияет на другие параметры!
        use_thinking = enable_thinking if enable_thinking is not None \
            else self.config.get("default_enable_thinking", False)
        
        # ВСЕ параметры независимы, берутся либо из переданных значений, либо из конфига
        final_max_tokens = max_tokens if max_tokens is not None \
            else self.config.get("default_max_tokens", 512)
        
        final_temperature = temperature if temperature is not None \
            else self.config.get("default_temperature", 0.7)
        
        final_top_p = top_p if top_p is not None \
            else self.config.get("default_top_p", 0.8)
        
        final_repetition_penalty = repetition_penalty if repetition_penalty is not None \
            else self.config.get("repetition_penalty", 1.1)
        
        final_top_k = top_k if top_k is not None \
            else self.config.get("top_k", 40)
        
        return {
            "max_tokens": final_max_tokens,
            "temperature": final_temperature,
            "top_p": final_top_p,
            "repetition_penalty": final_repetition_penalty,
            "top_k": final_top_k,
            "enable_thinking": use_thinking  # ← Только этот флаг!
        }