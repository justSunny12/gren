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
    
    SIMPLE_JS = """
    <script>
    function selectChat(chatId) {
        document.querySelectorAll('.chat-item').forEach(el => {
            el.classList.remove('active');
        });
        
        const clicked = document.querySelector(`[data-chat-id="${chatId}"]`);
        if (clicked) {
            clicked.classList.add('active');
        }
        
        const targetDiv = document.getElementById('chat_input_field');
        if (targetDiv) {
            const textarea = targetDiv.querySelector('textarea');
            if (textarea) {
                textarea.value = chatId;
                
                ['input', 'change'].forEach((eventName, index) => {
                    setTimeout(() => {
                        try {
                            const event = new Event(eventName, { 
                                bubbles: true,
                                cancelable: true 
                            });
                            textarea.dispatchEvent(event);
                        } catch (e) {}
                    }, index * 50 + 50);
                });
            }
        }
    }
    
    function renderChatList(chats) {
        const container = document.getElementById('chat_list');
        if (!container) {
            setTimeout(() => renderChatList(chats), 1000);
            return;
        }
        
        if (typeof chats === 'string') {
            try {
                chats = JSON.parse(chats);
            } catch (e) {
                chats = [];
            }
        }
        
        window.chatListData = chats || [];
        
        container.innerHTML = '';
        
        if (!window.chatListData || window.chatListData.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 40px 20px; color: #64748b;">
                    <div style="font-size: 48px; margin-bottom: 20px;">💬</div>
                    <div style="font-size: 16px; font-weight: 600; margin-bottom: 10px;">Нет чатов</div>
                    <div style="font-size: 14px;">Создайте новый чат</div>
                </div>
            `;
            return;
        }
        
        window.chatListData.forEach((chat) => {
            const chatDiv = document.createElement('div');
            chatDiv.className = 'chat-item';
            chatDiv.setAttribute('data-chat-id', chat.id);
            
            let timeInfo = '';
            if (chat.updated) {
                try {
                    const date = new Date(chat.updated);
                    timeInfo = ` • ${date.toLocaleDateString()} ${date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;
                } catch (e) {}
            }
            
            chatDiv.innerHTML = `
                <div style="display: flex; align-items: center; gap: 12px; padding: 14px;">
                    <span style="font-size: 24px;">💬</span>
                    <div style="flex: 1; overflow: hidden;">
                        <div style="font-weight: 700; font-size: 17px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                            ${chat.name}
                        </div>
                        <div style="font-size: 14px; color: #666; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                            ID: ${chat.id} • ${chat.history_length || 0} сообщ.${timeInfo}
                        </div>
                    </div>
                </div>
            `;
            
            if (chat.is_current) {
                chatDiv.classList.add('active');
            }
            
            chatDiv.onclick = function() {
                const chatId = this.getAttribute('data-chat-id');
                selectChat(chatId);
            };
            
            container.appendChild(chatDiv);
        });
        
        const activeChat = window.chatListData.find(chat => chat.is_current);
        if (activeChat) {
            setTimeout(() => {
                selectChat(activeChat.id);
            }, 500);
        }
    }
    
    document.addEventListener('DOMContentLoaded', function() {});
    
    document.addEventListener('chatListUpdated', function() {
        if (window.chatListData && window.chatListData.length > 0) {
            renderChatList(window.chatListData);
        }
    });
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
        
        sidebar_components["delete_dialog_btn"].click(
            fn=ui_handlers.delete_chat_with_js_handler,
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
                    const chats = JSON.parse(data);
                    renderChatList(chats);
                } catch (e) {}
                return [];
            }
            """
        )
    
    return demo, css_content, SIMPLE_JS

def get_css_content():
    """Возвращает CSS контент для launch()"""
    return load_css()