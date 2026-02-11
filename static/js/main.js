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

// Закрываем контекстные меню при скролле
document.addEventListener('scroll', function(e) {
    if (window.closeAllContextMenus) {
        window.closeAllContextMenus();
    }
}, true);

// Закрываем контекстные меню при изменении размера окна
window.addEventListener('resize', function() {
    if (window.closeAllContextMenus) {
        window.closeAllContextMenus();
    }
});

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', function() {
    console.log('Main.js: DOM загружен');
    
    // Закрытие модального окна при клике на оверлей (дополнительная защита)
    document.addEventListener('click', function(e) {
        if (window.deleteConfirmationModal && window.deleteConfirmationModal.isVisible && 
            e.target.id === 'deleteConfirmModal') {
            window.deleteConfirmationModal.hide(false);
        }
        if (window.renameChatModal && window.renameChatModal.isVisible && 
            e.target.id === 'renameChatModal') {
            window.renameChatModal.hide(false);
        }
    });
    
    // Инициализация кнопок генерации
    if (window.initGenerationButtons) {
        setTimeout(() => {
            window.initGenerationButtons();
        }, 500);
    }
});

// Обработчик обновления списка чатов
document.addEventListener('chatListUpdated', function() {
    // Используем данные, которые могли быть установиться через Gradio
    if (window.chatListData && window.renderChatList) {
        window.renderChatList(window.chatListData);
    }
});

// Загружаем дополнительные модули после загрузки основных
setTimeout(() => {
    if (window.loadScript) {
        // Загружаем модальные окна если они еще не загружены
        if (!window.deleteConfirmationModal) {
            window.loadScript('static/js/modules/delete-modal.js');
        }
        if (!window.renameChatModal) {
            window.loadScript('static/js/modules/rename-modal.js');
        }
    }
}, 1000);