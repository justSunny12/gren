/* static/js/modules/utils.js - Вспомогательные функции */
if (!window.SELECTORS) {
    console.error('SELECTORS не определены! Загрузите selectors.js первым');
}

window.activeContextMenu = null;
window.lastChatClick = 0;

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

    document.querySelectorAll('.chat-item.context-menu-open').forEach(item => {
        item.classList.remove('context-menu-open');
    });

    document.querySelectorAll(`${window.SELECTORS.CONTEXT_MENU}.show`).forEach(menu => {
        menu.classList.remove('show');
        if (menu.parentNode) {
            menu.parentNode.removeChild(menu);
        }
    });

    document.querySelectorAll(`${window.SELECTORS.CONTEXT_MENU}`).forEach(menu => {
        if (menu.parentNode) {
            menu.parentNode.removeChild(menu);
        }
    });
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

// Функция для загрузки дополнительных JavaScript файлов
window.loadScript = function(src, callback) {
    if (document.querySelector(`script[src="${src}"]`)) {
        if (callback) callback();
        return;
    }
    const script = document.createElement('script');
    script.src = src;
    script.onload = function() {
        if (callback) callback();
    };
    script.onerror = function() {
        console.error(`Не удалось загрузить скрипт: ${src}`);
        if (callback) callback();
    };
    document.head.appendChild(script);
};

// НОВАЯ ФУНКЦИЯ: унифицированная отправка команд
window.sendCommand = function(command) {
    const chatInput = window.getChatInputField();
    if (!chatInput) {
        console.error('Не найдено поле ввода для отправки команды');
        return false;
    }
    chatInput.value = command;
    chatInput.dispatchEvent(new Event('input', { bubbles: true }));
    // Очищаем поле после отправки (опционально, как в генерации)
    setTimeout(() => {
        chatInput.value = '';
    }, 50);
    return true;
};

// Инициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', function() {
    if (!window.deleteConfirmationModal) {
        window.loadScript('static/js/modules/delete-modal.js');
    }
    if (!window.renameChatModal) {
        window.loadScript('static/js/modules/rename-modal.js');
    }
    if (!window.settingsModal) {
        window.loadScript('static/js/modules/settings-modal.js');
    }
});