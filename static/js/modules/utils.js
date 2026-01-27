/* static/js/modules/utils.js - Вспомогательные функции */
// Проверяем, что SELECTORS загружены
if (!window.SELECTORS) {
    console.error('SELECTORS не определены! Загрузите selectors.js первым');
}

// Глобальные переменные (используем window для доступа из других файлов)
window.activeContextMenu = null;
window.lastChatClick = 0;

// Вспомогательные функции
window.debounce = function(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

window.closeAllContextMenus = function() {
    if (!window.SELECTORS) return;
    
    // Закрываем все видимые меню
    document.querySelectorAll(`${window.SELECTORS.CONTEXT_MENU}.show`).forEach(menu => {
        menu.classList.remove('show');
        // Удаляем меню из DOM через небольшой таймаут
        setTimeout(() => {
            if (menu.parentNode) {
                menu.parentNode.removeChild(menu);
            }
        }, 100);
    });
    
    // Также удаляем все меню, даже скрытые (на всякий случай)
    document.querySelectorAll(`${window.SELECTORS.CONTEXT_MENU}`).forEach(menu => {
        if (menu.parentNode) {
            menu.parentNode.removeChild(menu);
        }
    });
    
    window.activeContextMenu = null;
};

window.getChatInputField = function() {
    if (!window.SELECTORS) return null;
    
    const targetDiv = document.getElementById(window.SELECTORS.CHAT_INPUT_FIELD.replace('#', ''));
    return targetDiv ? targetDiv.querySelector('textarea') : null;
};

window.escapeHtml = function(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
};