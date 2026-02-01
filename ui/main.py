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
        except Exception:
            pass
    
    return css_content

def reset_user_settings():
    """Сбрасывает пользовательские настройки к стандартным"""
    try:
        config_service = container.get("config_service")
        success = config_service.reset_user_settings()
        
        if success:
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
    except Exception:
        return None, None, None, "⚠️ Ошибка сброса настроек"

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
        'static/js/main.js'                   # 7. Основной код
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

    // Функция для добавления SVG иконки в круглую кнопку
    function setupSendButtonIcon() {{
        const sendButtons = document.querySelectorAll('.send-btn-wrapper button');
        sendButtons.forEach(button => {{
            // Очищаем кнопку от всего
            button.innerHTML = '';
            
            // Создаем ваш точный SVG
            const svgNS = 'http://www.w3.org/2000/svg';
            const svg = document.createElementNS(svgNS, 'svg');
            
            // Устанавливаем ВСЕ атрибуты как в вашем SVG
            svg.setAttribute('xmlns', svgNS);
            svg.setAttribute('width', '20');
            svg.setAttribute('height', '20');
            svg.setAttribute('viewBox', '0 0 24 24');
            svg.setAttribute('fill', 'none');
            svg.setAttribute('stroke', 'currentColor');
            svg.setAttribute('stroke-width', '2');
            svg.setAttribute('stroke-linecap', 'round');
            svg.setAttribute('stroke-linejoin', 'round');
            svg.setAttribute('class', 'lucide lucide-arrow-up-icon lucide-arrow-up');
            
            // Первый path
            const path1 = document.createElementNS(svgNS, 'path');
            path1.setAttribute('d', 'm5 12 7-7 7 7');
            
            // Второй path
            const path2 = document.createElementNS(svgNS, 'path');
            path2.setAttribute('d', 'M12 19V5');
            
            // Добавляем path в SVG
            svg.appendChild(path1);
            svg.appendChild(path2);
            
            // Добавляем SVG в кнопку
            button.appendChild(svg);
            
            // Стили для SVG чтобы он был белым и правильно позиционировался
            svg.style.width = '20px';
            svg.style.height = '20px';
            svg.style.display = 'block';
            svg.style.color = 'white';  // Устанавливаем цвет через CSS
            svg.style.stroke = 'currentColor';  // Используем currentColor для stroke
        }});
    }}

    // Запускаем сразу и периодически проверяем
    function initButtons() {{
        setupSendButtonIcon();
        
        // Дополнительная проверка через интервалы
        setTimeout(setupSendButtonIcon, 100);
        setTimeout(setupSendButtonIcon, 500);
        setTimeout(setupSendButtonIcon, 1000);
        setTimeout(setupSendButtonIcon, 2000);
    }}

    // Запускаем при загрузке
    document.addEventListener('DOMContentLoaded', initButtons);

    // И при обновлении интерфейса Gradio
    if (window.gradio_app) {{
        document.addEventListener('gradio_update', initButtons);
    }}

    // MutationObserver для отслеживания динамических изменений
    const buttonObserver = new MutationObserver(function(mutations) {{
        mutations.forEach(function(mutation) {{
            if (mutation.type === 'childList') {{
                // Проверяем, добавились ли новые кнопки
                const hasNewButtons = mutation.addedNodes && Array.from(mutation.addedNodes).some(node => {{
                    return node.classList && node.classList.contains('send-btn-wrapper') ||
                        node.querySelector && node.querySelector('.send-btn-wrapper');
                }});
                
                if (hasNewButtons) {{
                    setTimeout(setupSendButtonIcon, 100);
                }}
            }}
        }});
    }});

    // Начинаем наблюдение
    buttonObserver.observe(document.body, {{
        childList: true,
        subtree: true
    }});

    // Также запускаем при кликах и фокусе (на всякий случай)
    document.addEventListener('click', function() {{
        setTimeout(setupSendButtonIcon, 50);
    }});

    document.addEventListener('focus', function() {{
        setTimeout(setupSendButtonIcon, 50);
    }}, true);
    </script>
    """
    
    with gr.Blocks(title="Qwen3-4B Chat", fill_width=True) as demo:
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
                sidebar_components["status_text"],
                chat_list_data
            ]
        )
        
        sidebar_components["chat_input"].change(
            fn=ui_handlers.handle_chat_selection,
            inputs=[sidebar_components["chat_input"]],
            outputs=[
                chatbot,
                current_dialog_id,
                sidebar_components["status_text"],
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
                sidebar_components["status_text"],
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
                sidebar_components["enable_thinking"],
                sidebar_components["status_text"]
            ]
        )
        
        def on_slider_change(max_tokens, temperature, enable_thinking):
            return ui_handlers.save_user_settings_handler(max_tokens, temperature, enable_thinking)
        
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
        
        def send_message(prompt, chat_id, max_tokens, temperature, enable_thinking):
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
                chatbot,
                user_input,
                current_dialog_id,
                chatbot,
                chat_list_data
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
                chatbot,
                user_input,
                current_dialog_id,
                chatbot,
                chat_list_data
            ]
        )
        
        demo.load(
            fn=ui_handlers.init_app_handler,
            outputs=[
                chatbot,
                current_dialog_id,
                chatbot,
                sidebar_components["max_tokens"],
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

def get_css_content():
    """Возвращает CSS контент для launch()"""
    return load_css()