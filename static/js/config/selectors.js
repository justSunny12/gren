/* static/js/config/selectors.js - Централизованные селекторы */

// Используем IIFE и проверяем, не объявлены ли уже переменные
(function() {
    // Проверяем, не существует ли уже SELECTORS в глобальной области
    if (window.SELECTORS !== undefined) {
        console.warn('SELECTORS уже объявлены в глобальной области');
        return;
    }
    
    window.SELECTORS = {
        CHAT_LIST: '#chat_list',
        CHAT_INPUT_FIELD: '#chat_input_field',
        CHAT_ITEM: '.chat-item',
        CHAT_CONTROL: '.chat-control',
        CONTEXT_MENU: '.chat-context-menu',
        CONTEXT_MENU_ITEM: '.chat-context-menu-item',
        CHAT_NAME: '.chat-name',
        GROUP_DIVIDER: '.group-divider',
        NEW_CHAT_BTN: '.new-chat-btn'  // Добавляем для создания нового чата
    };

    // Константы для дебаунса
    window.SWITCH_DEBOUNCE_MS = 300;
    window.INPUT_DEBOUNCE_MS = 500;
})();