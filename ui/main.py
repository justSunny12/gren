# /ui/main.py
import gradio as gr
import os
from ui.layouts.main_layout import create_main_layout
from logic.ui_handlers import ui_handlers

def load_css():
    """Загружает все CSS файлы"""
    css_files = [
        'css/base.css',
        'css/sidebar.css', 
        'css/chat_window.css',
        'css/input_area.css'
    ]
    
    css_content = ""
    
    for css_file in css_files:
        try:
            if os.path.exists(css_file):
                with open(css_file, 'r', encoding='utf-8') as f:
                    css_content += f.read() + "\n"
            else:
                print(f"⚠️ CSS файл не найден: {css_file}")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки CSS файла {css_file}: {e}")
    
    return css_content

def create_main_ui():
    """Создает основной UI интерфейс с привязанной логикой"""
    
    # Загружаем CSS (но не передаем в Blocks)
    css_content = load_css()
    
    # Убираем css из gr.Blocks() - только title
    with gr.Blocks(title="Qwen3-4B Chat") as demo:
        current_dialog_id = gr.State(value=None)
        
        # Создаем layout
        sidebar_components, chatbot, user_input, submit_btn = create_main_layout()
        
        # 1. Создание нового чата - 6 OUTPUTS
        sidebar_components["create_dialog_btn"].click(
            fn=ui_handlers.create_chat_handler,
            inputs=[],
            outputs=[
                chatbot,           # 0 - история чата
                user_input,        # 1 - очистить поле ввода
                current_dialog_id, # 2 - ID текущего диалога
                sidebar_components["dialog_dropdown"],  # 3 - обновить dropdown
                sidebar_components["status_text"],      # 4 - обновить статус
                chatbot            # 5 - обновить label чата
            ]
        )
        
        # 2. Переключение чата - 6 OUTPUTS
        sidebar_components["switch_dialog_btn"].click(
            fn=ui_handlers.switch_chat_handler,
            inputs=[sidebar_components["dialog_dropdown"]],
            outputs=[
                chatbot,
                user_input,
                current_dialog_id,
                sidebar_components["dialog_dropdown"],
                sidebar_components["status_text"],
                chatbot
            ]
        )
        
        # 3. Удаление чата - 6 OUTPUTS
        sidebar_components["delete_dialog_btn"].click(
            fn=ui_handlers.delete_chat_handler,
            inputs=[sidebar_components["dialog_dropdown"]],
            outputs=[
                chatbot,
                user_input,
                current_dialog_id,
                sidebar_components["dialog_dropdown"],
                sidebar_components["status_text"],
                chatbot
            ]
        )
        
        # 4. Функция отправки сообщения - ТОЛЬКО 5 OUTPUTS
        def send_message(prompt, chat_id, max_tokens, temperature, enable_thinking):
            """Обертка для отправки сообщения"""
            return ui_handlers.send_message_handler(
                prompt, 
                chat_id, 
                max_tokens, 
                temperature,
                enable_thinking
            )

        # 5. Отправка по кнопке - ТОЛЬКО 5 OUTPUTS
        submit_btn.click(
            fn=send_message,
            inputs=[
                user_input, 
                current_dialog_id,
                sidebar_components["max_tokens"],
                sidebar_components["temperature"],
                sidebar_components["enable_thinking"]  # ← ДОБАВЛЯЕМ
            ],
            outputs=[
                chatbot,           # 0 - история чата
                user_input,        # 1 - очистить поле ввода
                current_dialog_id, # 2 - ID текущего диалога
                sidebar_components["dialog_dropdown"],  # 3 - обновить dropdown
                chatbot            # 4 - обновить label чата
            ]
        )

        # 6. Отправка по Enter - ТОЛЬКО 5 OUTPUTS
        user_input.submit(
            fn=send_message,
            inputs=[
                user_input, 
                current_dialog_id,
                sidebar_components["max_tokens"],
                sidebar_components["temperature"],
                sidebar_components["enable_thinking"]  # ← ДОБАВЛЯЕМ
            ],
            outputs=[
                chatbot,
                user_input,
                current_dialog_id,
                sidebar_components["dialog_dropdown"],
                chatbot
            ]
        )
        
        # 7. Инициализация - ТОЛЬКО 4 OUTPUTS
        demo.load(
            fn=ui_handlers.init_app_handler,
            outputs=[
                chatbot,           # 0 - история чата
                current_dialog_id, # 1 - ID текущего диалога
                sidebar_components["dialog_dropdown"],  # 2 - обновить dropdown
                chatbot            # 3 - обновить label чата
            ]
        )
    
    return demo, css_content

def get_css_content():
    """Возвращает CSS контент для launch()"""
    return load_css()