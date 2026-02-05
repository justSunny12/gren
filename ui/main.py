# /ui/main.py
import gradio as gr
import os
from ui.layouts.main_layout import create_main_layout
from handlers import ui_handlers
from container import container

def load_css():
    """Загружает все CSS файлы из static/css/"""
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
    """Тихий сброс пользовательских настроек к стандартным"""
    try:
        config_service = container.get("config_service")
        success = config_service.reset_user_settings()

        if success:
            default_config = config_service.get_default_config()
            gen_config = default_config.get("generation", {})

            # Возвращаем обновленные значения для всех трёх параметров
            return (
                gen_config.get("default_max_tokens", 512),
                gen_config.get("default_temperature", 0.7),
                gen_config.get("default_enable_thinking", False)
            )
        else:
            return gr.update(), gr.update(), gr.update()
    except Exception:
        return gr.update(), gr.update(), gr.update()

def on_slider_change(max_tokens, temperature, enable_thinking):
    """Тихий обработчик изменения параметров - сохраняет настройки без сообщений"""
    try:
        config_service = container.get("config_service")
        config_service.update_user_settings_batch({
            "generation": {
                "max_tokens": max_tokens,
                "temperature": temperature,
                "enable_thinking": enable_thinking
            }
        })
        return gr.update(), gr.update(), gr.update()
    except Exception:
        return gr.update(), gr.update(), gr.update()

def create_main_ui():
    """Создает основной UI интерфейс с привязанной логикой"""
    
    css_content = load_css()
    
    # Загружаем JavaScript из файлов
    js_files = [
        'static/js/config/selectors.js',      # 1. Селекторы (самый первый!)
        'static/js/modules/utils.js',         # 2. Утилиты
        'static/js/modules/delete-modal.js',  # 3. Модальное окно удаления
        'static/js/modules/rename-modal.js',  # 4. Модальное окно переименования
        'static/js/modules/chat-list.js',     # 5. Список чатов
        'static/js/modules/context-menu.js',  # 6. Контекстное меню
        'static/js/modules/send-button.js',   # 7. Модуль для круглой кнопки отправки (НОВЫЙ)
        'static/js/main.js'                   # 8. Основной код
    ]
    
    js_content = ""
    for js_file in js_files:
        try:
            if os.path.exists(js_file):
                with open(js_file, 'r', encoding='utf-8') as f:
                    js_content += f.read() + "\n\n"
            else:
                print(f"⚠️ JS файл не найден: {js_file}")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки JS файла {js_file}: {e}")
    
    # JavaScript для добавления иконки в круглую кнопку
    JS_CODE = f"""
    <script type="text/javascript">
    {js_content}
    </script>
    """
    
    with gr.Blocks(title="Qwen3-30B Chat", fill_width=True) as demo:
        current_dialog_id = gr.State(value=None)
        
        sidebar_components, chatbot, user_input, submit_btn = create_main_layout()
        
        chat_list_data = gr.Textbox(
            visible=False,
            elem_id="chat_list_data",
            interactive=False
        )
        
        sidebar_components["chat_input"].input(
            fn=ui_handlers.handle_chat_selection,
            inputs=[sidebar_components["chat_input"]],
            outputs=[
                chatbot,
                current_dialog_id,
                chat_list_data
            ]
        )
        
        sidebar_components["chat_input"].change(
            fn=ui_handlers.handle_chat_selection,
            inputs=[sidebar_components["chat_input"]],
            outputs=[
                chatbot,
                current_dialog_id,
                chat_list_data
            ]
        )
        
        sidebar_components["create_dialog_btn"].click(
            fn=ui_handlers.create_chat_with_js_handler,
            inputs=[],
            outputs=[
                chatbot,
                user_input,
                current_dialog_id,
                sidebar_components["js_trigger"],
                chat_list_data
            ]
        )
        
        sidebar_components["reset_settings_btn"].click(
            fn=reset_user_settings,
            inputs=[],
            outputs=[
                sidebar_components["max_tokens"],
                sidebar_components["temperature"],
                sidebar_components["enable_thinking"]
            ]
        )
        
        # Восстанавливаем change события для параметров
        for param in ["max_tokens", "temperature", "enable_thinking"]:
            sidebar_components[param].change(
                fn=on_slider_change,
                inputs=[
                    sidebar_components["max_tokens"],
                    sidebar_components["temperature"],
                    sidebar_components["enable_thinking"]
                ],
                outputs=[
                    sidebar_components["max_tokens"],
                    sidebar_components["temperature"],
                    sidebar_components["enable_thinking"]
                ]
            )
        
        def send_message(prompt, chat_id, max_tokens, temperature, enable_thinking):
            # Обёртка для вызова ui_handlers.send_message_handler
            return ui_handlers.send_message_handler(
                prompt, 
                chat_id, 
                max_tokens, 
                temperature,
                enable_thinking
            )

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
                chatbot,          # history
                user_input,       # очистка ввода
                current_dialog_id, # new_chat_id
                chat_list_data    # данные списка чатов
            ]
        )

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
                chatbot,          # history
                user_input,       # очистка ввода
                current_dialog_id, # new_chat_id
                chat_list_data    # данные списка чатов
            ]
        )
        
        demo.load(
            fn=ui_handlers.init_app_handler,
            outputs=[
                chatbot,          # history
                current_dialog_id, # chat_id
                sidebar_components["max_tokens"],  # было: chatbot для chat_name
                sidebar_components["temperature"],
                sidebar_components["enable_thinking"],
                chat_list_data
            ]
        )
        
        chat_list_data.change(
            fn=None,
            inputs=[chat_list_data],
            outputs=[],
            js="""
            (data) => {
                try {
                    if (window.renderChatList) {
                        window.renderChatList(data);
                    }
                } catch (e) {
                    console.error('Ошибка рендеринга списка чатов:', e);
                }
                return [];
            }
            """
        )
    
    return demo, css_content, JS_CODE