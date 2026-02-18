/* static/js/modules/utils.js - Вспомогательные функции */
if (!window.SELECTORS) {
    console.error('SELECTORS не определены! Загрузите selectors.js первым');
}

window.activeContextMenu = null;
window.lastChatClick = 0;

// Дебаунс
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

// Закрыть все контекстные меню
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

// Получить поле ввода чата
window.getChatInputField = function() {
    if (!window.SELECTORS) return null;
    const targetDiv = document.getElementById(window.SELECTORS.CHAT_INPUT_FIELD.replace('#', ''));
    return targetDiv ? targetDiv.querySelector('textarea') : null;
};

// Экранирование HTML
window.escapeHtml = function(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
};

// Загрузка дополнительных JS-файлов
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

// Унифицированная отправка команд с логом
window.sendCommand = function(command) {
    const chatInput = window.getChatInputField();
    if (!chatInput) {
        console.error('Не найдено поле ввода для отправки команды');
        return false;
    }
    chatInput.value = command;
    chatInput.dispatchEvent(new Event('input', { bubbles: true }));
    setTimeout(() => {
        chatInput.value = '';
    }, 50);
    return true;
};

// Инициализация приложения
document.addEventListener('DOMContentLoaded', function() {
    // Загружаем модальные окна, если они ещё не загружены
    if (!window.deleteConfirmationModal) {
        window.loadScript('static/js/modules/delete-modal.js');
    }
    if (!window.renameChatModal) {
        window.loadScript('static/js/modules/rename-modal.js');
    }
    if (!window.settingsModal) {
        window.loadScript('static/js/modules/settings-modal.js');
    }

    // Кэшируем настройки из скрытого поля settings_data
    const checkSettingsInterval = setInterval(() => {
        const settingsDataElem = document.querySelector('#settings_data');
        if (settingsDataElem && settingsDataElem.value) {
            try {
                let settings = settingsDataElem.value;
                if (typeof settings === 'string') {
                    settings = JSON.parse(settings);
                }
                window.appSettings = settings;
                clearInterval(checkSettingsInterval);
            } catch (e) {
                console.error('Ошибка парсинга settings_data:', e);
            }
        }
    }, 100);

    // Дополнительно: слушаем событие change на самом компоненте Gradio (на случай обновления)
    const settingsDataElem = document.querySelector('#settings_data');
    if (settingsDataElem) {
        document.addEventListener('gradio_update', function() {
            const elem = document.querySelector('#settings_data');
            if (elem && elem.value) {
                try {
                    let settings = elem.value;
                    if (typeof settings === 'string') {
                        settings = JSON.parse(settings);
                    }
                    window.appSettings = settings;
                } catch (e) {
                    console.error('Ошибка обновления настроек:', e);
                }
            }
        });
    }
});