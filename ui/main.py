# /ui/main.py
import gradio as gr
import os
from ui.layouts.main_layout import create_main_layout
from logic.ui_handlers import ui_handlers
from container import container

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

def reset_user_settings():
    """Сбрасывает пользовательские настройки к стандартным"""
    try:
        config_service = container.get("config_service")
        success = config_service.reset_user_settings()
        
        if success:
            # Загружаем стандартные значения
            default_config = config_service.get_default_config()
            gen_config = default_config.generation
            
            return (
                gen_config.default_max_tokens,
                gen_config.default_temperature,
                gen_config.default_enable_thinking,
                "✅ Настройки сброшены к стандартным"
            )
        else:
            return None, None, None, "❌ Ошибка сброса настроек"
            
    except Exception as e:
        print(f"Ошибка при сбросе настроек: {e}")
        return None, None, None, f"⚠️ Ошибка: {str(e)}"

def create_main_ui():
    """Создает основной UI интерфейс с привязанной логикой"""
    
    # Загружаем CSS (но не передаем в Blocks)
    css_content = load_css()
    
    # Убираем css из gr.Blocks() - только title
    with gr.Blocks(title="Qwen3-4B Chat") as demo:
        current_dialog_id = gr.State(value=None)
        
        # Создаем layout
        sidebar_components, chatbot, user_input, submit_btn = create_main_layout()
        
        # Создаем скрытый триггер для автосохранения
        auto_save_trigger = gr.Textbox(visible=False, elem_id="auto_save_trigger")
        
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
        
        # 4. Сброс пользовательских настроек - 4 OUTPUTS
        sidebar_components["reset_settings_btn"].click(
            fn=reset_user_settings,
            inputs=[],
            outputs=[
                sidebar_components["max_tokens"],
                sidebar_components["temperature"],
                sidebar_components["enable_thinking"],
                sidebar_components["status_text"]
            ]
        )
        
        # 5. Автосохранение настроек при изменении слайдеров
        def on_slider_change(max_tokens, temperature, enable_thinking):
            """Вызывается при изменении любого параметра"""
            return ui_handlers.save_user_settings_handler(max_tokens, temperature, enable_thinking)
        
        # Привязываем автосохранение к изменениям всех трех параметров
        for param in ["max_tokens", "temperature", "enable_thinking"]:
            sidebar_components[param].change(
                fn=on_slider_change,
                inputs=[
                    sidebar_components["max_tokens"],
                    sidebar_components["temperature"],
                    sidebar_components["enable_thinking"]
                ],
                outputs=sidebar_components["status_text"]
            )
        
        # 6. Функция отправки сообщения - ТОЛЬКО 5 OUTPUTS
        def send_message(prompt, chat_id, max_tokens, temperature, enable_thinking):
            """Обертка для отправки сообщения"""
            return ui_handlers.send_message_handler(
                prompt, 
                chat_id, 
                max_tokens, 
                temperature,
                enable_thinking
            )

        # 7. Отправка по кнопке - ТОЛЬКО 5 OUTPUTS
        submit_btn.click(
            fn=send_message,
            inputs=[
                user_input, 
                current_dialog_id,
                sidebar_components["max_tokens"],
                sidebar_components["temperature"],
                sidebar_components["enable_thinking"]
            ],
            outputs=[
                chatbot,           # 0 - история чата
                user_input,        # 1 - очистить поле ввода
                current_dialog_id, # 2 - ID текущего диалога
                sidebar_components["dialog_dropdown"],  # 3 - обновить dropdown
                chatbot            # 4 - обновить label чата
            ]
        )

        # 8. Отправка по Enter - ТОЛЬКО 5 OUTPUTS
        user_input.submit(
            fn=send_message,
            inputs=[
                user_input, 
                current_dialog_id,
                sidebar_components["max_tokens"],
                sidebar_components["temperature"],
                sidebar_components["enable_thinking"]
            ],
            outputs=[
                chatbot,
                user_input,
                current_dialog_id,
                sidebar_components["dialog_dropdown"],
                chatbot
            ]
        )
        
        # 9. Инициализация - 7 OUTPUTS (добавлены значения для слайдеров)
        demo.load(
            fn=ui_handlers.init_app_handler,
            outputs=[
                chatbot,           # 0 - история чата
                current_dialog_id, # 1 - ID текущего диалога
                sidebar_components["dialog_dropdown"],  # 2 - обновить dropdown
                chatbot,           # 3 - обновить label чата
                sidebar_components["max_tokens"],       # 4 - значение слайдера токенов
                sidebar_components["temperature"],      # 5 - значение слайдера температуры
                sidebar_components["enable_thinking"]   # 6 - значение чекбокса thinking
            ]
        )
    
    return demo, css_content

def get_css_content():
    """Возвращает CSS контент для launch()"""
    return load_css()