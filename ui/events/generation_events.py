# ui/events/generation_events.py
import gradio as gr

class GenerationEvents:
    """Обработчики событий генерации (специально для JS триггеров)"""
    
    @staticmethod
    def bind_generation_js_events(generation_js_trigger):
        """Привязывает события для JS триггера генерации"""
        return generation_js_trigger.change(
            fn=None,
            inputs=[generation_js_trigger],
            outputs=[],
            js="""
            (jsCode) => {
                // Проверяем, есть ли JS код для выполнения
                if (jsCode && jsCode.trim() !== '') {
                    
                    // Извлекаем содержимое из тегов <script>, если они есть
                    let codeToExecute = jsCode;
                    
                    // Проверяем, содержит ли строка теги <script>
                    const scriptMatch = jsCode.match(/<script>(.*?)<\/script>/s);
                    if (scriptMatch && scriptMatch[1]) {
                        codeToExecute = scriptMatch[1].trim();
                    }
                    
                    // Выполняем код
                    try {
                        eval(codeToExecute);
                    } catch (e) {
                        console.error('Ошибка выполнения JS кода:', e);
                        console.error('Код, вызвавший ошибку:', codeToExecute);
                    }
                }
                return [];
            }
            """
        )