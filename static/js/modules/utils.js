/* static/js/modules/utils.js */
// Глобальные переменные и утилиты
let activeContextMenu = null;
let lastChatClick = 0;
const SWITCH_DEBOUNCE_MS = 300;

// Селекторы
const SELECTORS = {
    CHAT_LIST: '#chat_list',
    CHAT_INPUT_FIELD: '#chat_input_field',
    DELETE_BTN: '.delete-chat-btn',
    CHAT_ITEM: '.chat-item',
    CHAT_CONTROL: '.chat-control',
    CONTEXT_MENU: '.chat-context-menu',
    CONTEXT_MENU_ITEM: '.chat-context-menu-item'
};

// Вспомогательные функции
export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

export function closeAllContextMenus() {
    document.querySelectorAll(`${SELECTORS.CONTEXT_MENU}.show`).forEach(menu => {
        menu.classList.remove('show');
    });
    activeContextMenu = null;
}

export function getChatInputField() {
    const targetDiv = document.getElementById('chat_input_field'.replace('#', ''));
    return targetDiv ? targetDiv.querySelector('textarea') : null;
}

export { activeContextMenu, lastChatClick, SWITCH_DEBOUNCE_MS, SELECTORS };