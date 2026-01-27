/* static/js/main.js - Основной файл JavaScript */
// Проверяем, что SELECTORS загружены
if (!window.SELECTORS) {
    console.error('SELECTORS не определены! Загрузите selectors.js первым');
}

// Функция для выбора чата
window.selectChat = function(chatId) {
    // Защита от быстрых кликов
    if (window.lastChatClick && Date.now() - window.lastChatClick < window.SWITCH_DEBOUNCE_MS) {
        return;
    }
    window.lastChatClick = Date.now();
    
    if (!window.SELECTORS) return;
    
    document.querySelectorAll(window.SELECTORS.CHAT_ITEM).forEach(el => {
        el.classList.remove('active');
    });
    
    const clicked = document.querySelector(`[data-chat-id="${chatId}"]`);
    if (clicked) {
        clicked.classList.add('active');
    }
    
    const textarea = window.getChatInputField ? window.getChatInputField() : null;
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
};

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', function() {
    console.log('Chat UI JavaScript загружен');
    console.log('SELECTORS доступны:', window.SELECTORS);
});

// Обработчик обновления списка чатов
document.addEventListener('chatListUpdated', function() {
    // Используем данные, которые могли быть установлены через Gradio
    if (window.chatListData && window.chatListData.length > 0 && window.renderChatList) {
        window.renderChatList(window.chatListData);
    }
});