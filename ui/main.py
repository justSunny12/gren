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
    // Глобальные переменные для управления контекстными меню
    let activeContextMenu = null;
    
    function selectChat(chatId) {
        // Защита от быстрых кликов
        if (window.lastChatClick && Date.now() - window.lastChatClick < 300) {
            return;
        }
        window.lastChatClick = Date.now();
        
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
                
                // Запускаем событие сразу, без задержек
                try {
                    const event = new Event('input', { 
                        bubbles: true,
                        cancelable: true 
                    });
                    textarea.dispatchEvent(event);
                } catch (e) {}
            }
        }
        
        // Закрываем все открытые меню при переключении чата
        closeAllContextMenus();
    }
    
    function closeAllContextMenus() {
        document.querySelectorAll('.chat-context-menu.show').forEach(menu => {
            menu.classList.remove('show');
        });
        activeContextMenu = null;
    }
    
    function createContextMenu(chatId, chatName) {
        const menu = document.createElement('div');
        menu.className = 'chat-context-menu';
        menu.setAttribute('data-chat-id', chatId);
        
        menu.innerHTML = `
            <div class="chat-context-menu-item rename">
                <span class="menu-icon">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M13 21h8"/>
                        <path d="m15 5 4 4"/>
                        <path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/>
                    </svg>
                </span>
                <span>Переименовать</span>
            </div>
            <div class="chat-context-menu-item pin">
                <span class="menu-icon">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 17v5"/>
                        <path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z"/>
                    </svg>
                </span>
                <span>Закрепить</span>
            </div>
            <div class="chat-context-menu-divider"></div>
            <div class="chat-context-menu-item delete">
                <span class="menu-icon">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M3 6h18"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        <path d="M10 11v6"/>
                        <path d="M14 11v6"/>
                    </svg>
                </span>
                <span>Удалить</span>
            </div>
        `;
        
        // Добавляем обработчики для пунктов меню
        const renameBtn = menu.querySelector('.rename');
        const pinBtn = menu.querySelector('.pin');
        const deleteBtn = menu.querySelector('.delete');
        
        renameBtn.onclick = function(e) {
            e.stopPropagation();
            console.log('Переименовать чат:', chatId, chatName);
            closeAllContextMenus();
        };
        
        pinBtn.onclick = function(e) {
            e.stopPropagation();
            console.log('Закрепить чат:', chatId, chatName);
            closeAllContextMenus();
        };
        
        deleteBtn.onclick = function(e) {
            e.stopPropagation();
            console.log('Удалить чат:', chatId, chatName);
            closeAllContextMenus();
        };
        
        return menu;
    }
    
    function toggleContextMenu(chatItem, chatId, chatName) {
        // Закрываем все открытые меню
        closeAllContextMenus();
        
        // Если кликнули на тот же элемент управления
        if (activeContextMenu && activeContextMenu.parentElement === chatItem) {
            activeContextMenu = null;
            return;
        }
        
        // Создаем и показываем новое меню
        const menu = createContextMenu(chatId, chatName);
        chatItem.appendChild(menu);
        menu.classList.add('show');
        activeContextMenu = menu;
        
        // Закрываем меню при клике вне его
        setTimeout(() => {
            const closeMenuHandler = (e) => {
                if (!menu.contains(e.target) && !chatItem.querySelector('.chat-control').contains(e.target)) {
                    closeAllContextMenus();
                    document.removeEventListener('click', closeMenuHandler);
                }
            };
            document.addEventListener('click', closeMenuHandler);
        }, 10);
    }
    
    function renderChatList(chats) {
        const container = document.getElementById('chat_list');
        if (!container) {
            setTimeout(() => renderChatList(chats), 50);
            return;
        }
        
        if (typeof chats === 'string') {
            try {
                chats = JSON.parse(chats);
            } catch (e) {
                chats = { groups: {}, flat: [] };
            }
        }
        
        window.chatListData = chats.flat || [];
        window.chatGroups = chats.groups || {};
        
        container.innerHTML = '';
        
        if (!window.chatGroups || Object.keys(window.chatGroups).length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 20px; color: #64748b;">
                    Нет чатов
                </div>
            `;
            return;
        }
        
        // Закрываем все открытые меню при обновлении списка
        closeAllContextMenus();
        
        // Отображаем группы в правильном порядке
        const groupOrder = ['Сегодня', 'Вчера', '7 дней', 'Месяц', 'Более месяца'];
        
        groupOrder.forEach(groupName => {
            if (window.chatGroups[groupName] && window.chatGroups[groupName].length > 0) {
                // Добавляем разделитель группы
                const divider = document.createElement('div');
                divider.className = 'group-divider';
                divider.textContent = groupName;
                container.appendChild(divider);
                
                // Добавляем чаты из этой группы
                window.chatGroups[groupName].forEach((chat) => {
                    const chatDiv = document.createElement('div');
                    chatDiv.className = 'chat-item';
                    chatDiv.setAttribute('data-chat-id', chat.id);
                    
                    // Новая структура с элементом управления
                    chatDiv.innerHTML = `
                        <div class="chat-name-wrapper">
                            <div class="chat-name">${chat.name}</div>
                        </div>
                        <div class="chat-control"></div>
                    `;
                    
                    if (chat.is_current) {
                        chatDiv.classList.add('active');
                    }
                    
                    // Клик на весь элемент чата
                    chatDiv.onclick = function(e) {
                        // Если кликнули на элемент управления или контекстное меню - не переключаем чат
                        if (e.target.classList.contains('chat-control') || 
                            e.target.closest('.chat-control') ||
                            e.target.classList.contains('chat-context-menu-item') ||
                            e.target.closest('.chat-context-menu')) {
                            e.stopPropagation();
                            return;
                        }
                        const chatId = this.getAttribute('data-chat-id');
                        selectChat(chatId);
                        closeAllContextMenus();
                    };
                    
                    // Обработчик для элемента управления
                    const controlBtn = chatDiv.querySelector('.chat-control');
                    controlBtn.onclick = function(e) {
                        e.stopPropagation();
                        const chatId = chatDiv.getAttribute('data-chat-id');
                        const chatName = chat.name;
                        toggleContextMenu(chatDiv, chatId, chatName);
                    };
                    
                    container.appendChild(chatDiv);
                });
            }
        });
        
        // Выделяем активный чат
        const activeChat = window.chatListData.find(chat => chat.is_current);
        if (activeChat) {
            selectChat(activeChat.id);
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