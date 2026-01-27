/* static/js/main.js */
import { renderChatList } from './modules/chat-list.js';
import { SELECTORS, lastChatClick, SWITCH_DEBOUNCE_MS, getChatInputField } from './modules/utils.js';

// Экспортируем функции для использования в модулях
export function selectChat(chatId) {
    // Защита от быстрых кликов
    if (window.lastChatClick && Date.now() - window.lastChatClick < SWITCH_DEBOUNCE_MS) {
        return;
    }
    window.lastChatClick = Date.now();
    
    document.querySelectorAll(SELECTORS.CHAT_ITEM).forEach(el => {
        el.classList.remove('active');
    });
    
    const clicked = document.querySelector(`[data-chat-id="${chatId}"]`);
    if (clicked) {
        clicked.classList.add('active');
    }
    
    const textarea = getChatInputField();
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

// Глобальные функции для использования в Gradio
window.renderChatList = renderChatList;
window.selectChat = selectChat;

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', function() {
    console.log('Chat UI JavaScript загружен');
});

// Обработчик обновления списка чатов
document.addEventListener('chatListUpdated', function() {
    if (window.chatListData && window.chatListData.length > 0) {
        renderChatList(window.chatListData);
    }
});