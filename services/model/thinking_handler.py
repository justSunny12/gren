"""
Обработка тегов размышлений <think>
"""
import re


class ThinkingHandler:
    """Обработчик тегов размышлений"""
    
    def process(self, text: str) -> str:
        """Форматирует текст размышлений с использованием HTML span"""
        think_pattern = r'<think>(.*?)</think>'
        
        def replace_with_span(match):
            think_text = match.group(1).strip()
            if not think_text:
                return ""
            
            # Разбиваем на строки и каждую строку оборачиваем в span
            lines = think_text.split('\n')
            span_lines = []
            for line in lines:
                line = line.strip()
                if line:
                    span_lines.append(f"<span class='thinking-text'>{line}</span>")
                else:
                    span_lines.append('')
            
            return '\n'.join(span_lines)
        
        text = re.sub(think_pattern, replace_with_span, text, flags=re.DOTALL)
        
        # Удаляем оставшиеся теги
        text = text.replace('<think>', '').replace('</think>', '')
        
        # Убираем множественные пустые строки
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()