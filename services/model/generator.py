"""
Генерация ответов модели
"""
from typing import Dict, Any, List, Tuple
from mlx_lm import generate
from mlx_lm.sample_utils import make_sampler, make_logits_processors

def create_generation_components(params: Dict[str, Any]) -> Tuple[Any, Any]:
    """Создает sampler и logits_processors из параметров генерации."""
    sampler = make_sampler(
        temp=params["temperature"],
        top_p=params["top_p"],
        top_k=params["top_k"]
    )
    
    logits_processors = make_logits_processors(
        repetition_penalty=params["repetition_penalty"]
    )
    
    return sampler, logits_processors

class ResponseGenerator:
    """Генератор ответов модели"""
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        model,
        tokenizer,
        params: Dict[str, Any],
        thinking_handler = None
    ) -> str:
        """Генерирует ответ модели"""
        
        # Важно: enable_thinking в params влияет ТОЛЬКО на добавление тегов в промпт
        prompt = self._format_prompt(messages, tokenizer, params["enable_thinking"])
        
        # Создаем сэмплер из ВСЕХ параметров (они независимы от enable_thinking)
        sampler = make_sampler(
            temp=params["temperature"],      # ← Берётся как есть
            top_p=params["top_p"],          # ← Берётся как есть
            top_k=params["top_k"]           # ← Берётся как есть
        )
        
        logits_processors = make_logits_processors(
            repetition_penalty=params["repetition_penalty"]  # ← Берётся как есть
        )
        
        # Генерируем с независимыми параметрами
        try:
            response = generate(
                model=model,
                tokenizer=tokenizer,
                prompt=prompt,
                sampler=sampler,
                logits_processors=logits_processors,
                max_tokens=params["max_tokens"],  # ← Берётся как есть
                verbose=False
            )
            
            # Обрабатываем теги размышлений (если они есть)
            if thinking_handler and params["enable_thinking"]:
                response = thinking_handler.process(response.strip())
            else:
                response = response.strip()
            
            return response
            
        except Exception as e:
            print(f"❌ Ошибка генерации: {e}")
            raise
    
    def _format_prompt(
        self,
        messages: List[Dict[str, str]],
        tokenizer,
        enable_thinking: bool
    ) -> str:
        """Форматирует промпт для модели"""
        try:
            # enable_thinking влияет ТОЛЬКО на добавление тега <think>
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=enable_thinking  # ← ЕДИНСТВЕННОЕ влияние
            )
            return prompt
            
        except Exception:
            # Fallback на простую конкатенацию
            prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
            prompt += "\nassistant: "
            if enable_thinking:
                prompt += "<think>"  # ← ЕДИНСТВЕННОЕ влияние
            return prompt