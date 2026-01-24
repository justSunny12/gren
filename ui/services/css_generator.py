# /services/css_generator.py
import os
from typing import Dict, Any

class CSSGenerator:
    """Генератор CSS из конфигурации"""
    
    def __init__(self):
        # Ленивый импорт container
        from container import container
        self.config = container.get_config().ui
        self.paths_config = container.get_config().paths
    
    def generate_css(self) -> str:
        """Генерирует полный CSS код из конфигов"""
        css_parts = []
        
        # Базовые стили из конфига
        css_parts.append(self._generate_base_css())
        
        # Стили сайдбара
        css_parts.append(self._generate_sidebar_css())
        
        # Стили окна чата
        css_parts.append(self._generate_chat_window_css())
        
        # Стили области ввода
        css_parts.append(self._generate_input_area_css())
        
        # Собираем все вместе
        full_css = "\n".join(css_parts)
        
        # Сохраняем в файл (для отладки)
        self._save_css_to_file(full_css)
        
        return full_css
    
    def _generate_base_css(self) -> str:
        """Генерирует базовые стили"""
        return f"""
/* Авто-сгенерированный CSS из конфигурации */
/* Базовые сбросы и общие стили */

* {{
    box-sizing: border-box !important;
}}

body, html, .gradio-container {{
    margin: 0 !important;
    padding: 0 !important;
    height: 100vh !important;
    width: 100vw !important;
    overflow: hidden !important;
}}

/* Основной контейнер - жесткий контроль */
.gradio-container, 
.gradio-container > div,
.gradio-container > div > div {{
    height: 100vh !important;
    max-height: 100vh !important;
    min-height: 100vh !important;
}}

/* Основной ряд - занимает всю высоту */
.main-row {{
    height: 100vh !important;
    max-height: 100vh !important;
    min-height: 100vh !important;
    margin: 0 !important;
    padding: 0 !important;
    flex-wrap: nowrap !important;
}}

/* Основной контент - занимает оставшееся */
.main-content {{
    height: 100vh !important;
    max-height: 100vh !important;
    min-height: 100vh !important;
    padding: 0 !important;
    margin: 0 !important;
    flex: 1 !important;
    min-width: 0 !important;
    display: flex !important;
    flex-direction: column !important;
}}

/* Главный контейнер чата */
.chat-main-container {{
    height: calc(100vh - 20px) !important;
    max-height: calc(100vh - 20px) !important;
    min-height: calc(100vh - 20px) !important;
    padding: {self.config.chat_window.padding} !important;
    display: flex !important;
    flex-direction: column !important;
    flex: 1 !important;
    min-height: 0 !important;
    gap: 8px !important;
}}

/* Убираем стандартные стили Gradio */
.gr-box, .gr-form {{
    border: none !important;
    margin: 0 !important;
    padding: 0 !important;
}}

/* Фикс для flex элементов */
.wrap, .wrap.column {{
    height: auto !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}}

/* Убираем лишние отступы у Gradio элементов */
.gr-column, .gr-row {{
    margin: 0 !important;
    padding: 0 !important;
}}

/* Убираем outline у всех элементов при фокусе */
*:focus {{
    outline: none !important;
}}

/* Базовые настройки текста */
body {{
    font-family: {self.config.text.font_family} !important;
    font-size: {self.config.text.font_size} !important;
    line-height: {self.config.text.line_height} !important;
}}
"""
    
    def _generate_sidebar_css(self) -> str:
        """Генерирует стили сайдбара"""
        sidebar = self.config.sidebar
        
        return f"""
/* Стили сайдбара - сгенерировано из конфига */

#sidebar_container {{
    height: 100vh !important;
    max-height: 100vh !important;
    overflow-y: auto !important;
    padding: 10px 15px !important;
    border-right: 1px solid {sidebar.border_color} !important;
    background: {sidebar.background} !important;
    min-width: {sidebar.min_width} !important;
    width: {sidebar.width} !important;
    max-width: {sidebar.max_width} !important;
    flex-shrink: 0 !important;
}}

/* Разделитель в сайдбаре */
.sidebar-divider {{
    margin: 15px 0 !important;
    border-color: {sidebar.border_color} !important;
}}

/* Dropdown в сайдбаре */
#sidebar_container .gr-dropdown {{
    margin-top: 0 !important;
    margin-bottom: 15px !important;
}}

/* Кнопки в сайдбаре */
#sidebar_container .gr-button {{
    margin: 5px 0 !important;
}}

/* Аккордеон параметров */
#sidebar_container .params-accordion {{
    margin-top: 15px !important;
    margin-bottom: 15px !important;
}}

/* Статус внизу сайдбара */
#sidebar_container .gr-markdown:last-child {{
    margin-top: auto !important;
    margin-bottom: 10px !important;
}}

/* Стили кнопок из конфига */
.primary-btn {{
    background: {self.config.buttons.primary_color} !important;
    border: none !important;
    color: white !important;
}}

.primary-btn:hover {{
    background: {self.config.buttons.primary_hover} !important;
}}

.secondary-btn {{
    background: {self.config.buttons.secondary_color} !important;
    border: none !important;
    color: white !important;
}}

.danger-btn {{
    background: {self.config.buttons.danger_color} !important;
    border: none !important;
    color: white !important;
}}
"""
    
    def _generate_chat_window_css(self) -> str:
        """Генерирует стили окна чата"""
        chat = self.config.chat_window
        messages = self.config.messages
        
        return f"""
/* Стили окна чата - сгенерировано из конфига */

.chat-window-container {{
    flex: 1 !important;
    min-height: 0 !important;
    overflow-y: auto !important;
    border: 1px solid {chat.border_color} !important;
    border-radius: {chat.border_radius} !important;
    background: {chat.background} !important;
    box-sizing: border-box !important;
    padding: {chat.padding} !important;
}}

/* Чатбот */
.chat-window-container .chatbot {{
    display: flex !important;
    flex-direction: column !important;
    gap: 12px !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    background: transparent !important;
}}

/* Контейнеры сообщений */
.chat-window-container .chatbot > div {{
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    display: flex !important;
    width: 100% !important;
    min-height: auto !important;
    height: auto !important;
}}

/* СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЯ */
.chat-window-container .message.user {{
    background-color: {messages.user_bg} !important;
    border: 1px solid {messages.user_border} !important;
    border-radius: {messages.border_radius} {messages.border_radius} 0 {messages.border_radius} !important;
    padding: {messages.padding} !important;
    margin-left: auto !important;
    margin-right: 0 !important;
    max-width: {messages.max_width} !important;
    min-width: fit-content !important;
    word-wrap: break-word !important;
    white-space: pre-wrap !important;
    line-height: 1.4 !important;
    margin-bottom: 0 !important;
    padding-bottom: 10px !important;
    display: inline-block !important;
    position: relative !important;
}}

/* СООБЩЕНИЯ АССИСТЕНТА */
.chat-window-container .message.bot {{
    background-color: {messages.bot_bg} !important;
    border: 1px solid {messages.bot_border} !important;
    border-radius: {messages.border_radius} {messages.border_radius} {messages.border_radius} 0 !important;
    padding: {messages.padding} !important;
    margin-left: 0 !important;
    margin-right: auto !important;
    max-width: {messages.max_width} !important;
    min-width: fit-content !important;
    word-wrap: break-word !important;
    white-space: pre-wrap !important;
    line-height: 1.4 !important;
    margin-bottom: 0 !important;
    padding-bottom: 10px !important;
    display: inline-block !important;
    position: relative !important;
}}

/* КОНТЕЙНЕРЫ для разных типов */
.chat-window-container .chatbot > div[data-testid="user"] {{
    justify-content: flex-end !important;
    align-items: flex-start !important;
}}

.chat-window-container .chatbot > div[data-testid="bot"] {{
    justify-content: flex-start !important;
    align-items: flex-start !important;
}}

/* ВНУТРЕННИЕ ЭЛЕМЕНТЫ сообщений */
.chat-window-container .message {{
    display: inline-block !important;
    position: relative !important;
}}

/* Текст в сообщениях */
.chat-window-container .message p {{
    margin: 0 0 4px 0 !important;
    line-height: 1.4 !important;
    word-break: break-word !important;
}}

.chat-window-container .message p:last-child {{
    margin-bottom: 0 !important;
}}

/* Убираем пустые элементы */
.chat-window-container .message p:empty:not(:has(*)) {{
    display: none !important;
}}

/* Аватары */
.chat-window-container .avatar {{
    width: 32px !important;
    height: 32px !important;
    min-width: 32px !important;
    min-height: 32px !important;
    margin: 0 8px !important;
    align-self: flex-start !important;
}}

/* Стили для скроллбара чата */
.chat-window-container::-webkit-scrollbar {{
    width: 8px !important;
}}

.chat-window-container::-webkit-scrollbar-track {{
    background: #f8f9fa !important;
    border-radius: 4px !important;
}}

.chat-window-container::-webkit-scrollbar-thumb {{
    background: #ced4da !important;
    border-radius: 4px !important;
}}

.chat-window-container::-webkit-scrollbar-thumb:hover {{
    background: #adb5bd !important;
}}

/* ФИКС для Gradio контейнеров */
.chatbot .wrap.s {{
    margin: 0 !important;
    padding: 0 !important;
}}

.chat-window-container .chatbot > div .wrap,
.chat-window-container .chatbot > div .wrap.s,
.chat-window-container .chatbot > div .wrap.s.column {{
    margin: 0 !important;
    padding: 0 !important;
    gap: 0 !important;
    border: none !important;
}}

/* Просто скрываем ВСЕ кнопки с классом icon-button */
.chatbot .icon-button,
.chatbot button.icon-button {{
    display: none !important;
}}
"""
    
    def _generate_input_area_css(self) -> str:
        """Генерирует стили области ввода"""
        input_area = self.config.input_area
        
        return f"""
/* Стили области ввода - сгенерировано из конфига */

.input-plate {{
    flex-shrink: 0 !important;
    height: {input_area.height} !important;
    min-height: {input_area.min_height} !important;
    max-height: {input_area.max_height} !important;
    box-sizing: border-box !important;
    background: {input_area.background} !important;
    border: 1px solid {input_area.border_color} !important;
    border-radius: {input_area.border_radius} !important;
    display: flex !important;
    align-items: center !important;
}}

.input-row {{
    display: flex !important;
    align-items: center !important;
    gap: 0px !important;
    width: 100% !important;
    height: 100% !important;
    box-sizing: border-box !important;
    padding: 0 10px 0 0;
}}

.chat-input-wrapper {{
    flex: 1 !important;
    height: 100% !important;
    box-sizing: border-box !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    position: relative !important;
    display: flex !important;
    align-items: center !important;
}}

.chat-input-wrapper textarea {{
    width: 100% !important;
    height: 90px !important;
    min-height: 90px !important;
    max-height: 90px !important;
    box-sizing: border-box !important;
    resize: none !important;
    padding: 10px 14px !important;
    line-height: 1.4 !important;
    background: #f9f9f9 !important;
    border: 1px solid #d0d0d0 !important;
    border-radius: 6px !important;
    font-family: inherit !important;
    font-size: 14px !important;
    transition: all 0.2s ease !important;
    margin: 0 !important;
    display: block !important;
    overflow: hidden !important;
}}

.chat-input-wrapper textarea:hover {{
    border-color: #b0b0b0 !important;
    background: #f5f5f5 !important;
}}

.chat-input-wrapper textarea:focus {{
    border-color: {self.config.buttons.primary_color} !important;
    background: #fff !important;
    box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.1) !important;
    outline: none !important;
}}

.send-btn-wrapper {{
    height: 90px !important;
    width: 120px !important;
    min-width: 120px !important;
    max-width: 120px !important;
    flex-shrink: 0 !important;
    box-sizing: border-box !important;
    margin: 0 !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
}}

.send-btn-wrapper button {{
    width: 100% !important;
    height: 90px !important;
    margin: 0 !important;
    padding: 12px 8px !important;
    border-radius: 6px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    background: {self.config.buttons.primary_color} !important;
    border: none !important;
    color: white !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    line-height: 1.2 !important;
    text-align: center !important;
    white-space: normal !important;
    word-wrap: break-word !important;
}}

.send-btn-wrapper button:hover {{
    background: {self.config.buttons.primary_hover} !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
}}

.send-btn-wrapper button:active {{
    transform: translateY(0) !important;
    box-shadow: none !important;
}}

.send-btn-wrapper button:disabled {{
    background: #cccccc !important;
    cursor: not-allowed !important;
    transform: none !important;
    box-shadow: none !important;
}}
"""
    
    def _save_css_to_file(self, css_content: str):
        """Сохраняет сгенерированный CSS в файл для отладки"""
        debug_css_path = "generated_styles.css"
        try:
            with open(debug_css_path, 'w', encoding='utf-8') as f:
                f.write("/* АВТОГЕНЕРИРОВАННЫЙ CSS - НЕ РЕДАКТИРОВАТЬ */\n")
                f.write("/* Редактируйте config/ui_config.yaml */\n\n")
                f.write(css_content)
            print(f"✅ CSS сохранен в {debug_css_path}")
        except Exception as e:
            print(f"⚠️ Не удалось сохранить CSS: {e}")
    
    def load_existing_css(self) -> str:
        """Загружает существующие CSS файлы (для обратной совместимости)"""
        css_content = ""
        
        for css_file in self.paths_config.css_files:
            try:
                if os.path.exists(css_file):
                    with open(css_file, 'r', encoding='utf-8') as f:
                        css_content += f.read() + "\n"
                else:
                    print(f"⚠️ CSS файл не найден: {css_file}")
            except Exception as e:
                print(f"⚠️ Ошибка загрузки CSS файла {css_file}: {e}")
        
        # Если нет файлов, генерируем из конфига
        if not css_content:
            css_content = self.generate_css()
        
        return css_content

# Глобальный экземпляр
css_generator = CSSGenerator()