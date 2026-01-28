/* static/js/modules/context-menu.js */
// Проверяем, что SELECTORS загружены
if (!window.SELECTORS) {
    console.error('SELECTORS не определены! Загрузите selectors.js первым');
}

// Ждем загрузки DOM для инициализации модальных окон
document.addEventListener('DOMContentLoaded', function() {
    // Динамически загружаем модальные окна если они еще не загружены
    const loadScript = (src) => {
        if (!document.querySelector(`script[src="${src}"]`)) {
            const script = document.createElement('script');
            script.src = src;
            document.head.appendChild(script);
        }
    };
    
    // Загружаем delete-modal.js если еще не загружен
    if (!window.deleteConfirmationModal) {
        loadScript('static/js/modules/delete-modal.js');
    }
    
    // Загружаем rename-modal.js если еще не загружен
    if (!window.renameChatModal) {
        loadScript('static/js/modules/rename-modal.js');
    }
});

window.createContextMenu = function(chatId, chatName) {
    if (!window.SELECTORS) return null;
    
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
    setupMenuHandlers(menu, chatId, chatName);
    
    return menu;
};

function setupMenuHandlers(menu, chatId, chatName) {
    const renameBtn = menu.querySelector('.rename');
    const pinBtn = menu.querySelector('.pin');
    const deleteBtn = menu.querySelector('.delete');
    
    renameBtn.onclick = async function(e) {
        e.stopPropagation();
        
        // Находим родительский элемент чата и закрываем меню
        const chatItem = document.querySelector(`[data-chat-id="${chatId}"]`);
        if (chatItem && chatItem.classList.contains('context-menu-open')) {
            chatItem.classList.remove('context-menu-open');
        }
        
        if (menu.parentNode) {
            menu.parentNode.removeChild(menu);
        }
        
        // Используем кастомное модальное окно для переименования
        if (window.showRenameChatModal) {
            const newName = await window.showRenameChatModal(chatId, chatName);
            if (newName && newName !== chatName) {
                await renameChatRequest(chatId, newName);
            }
        } else {
            // Fallback на стандартный prompt если модальное окно не загружено
            const newName = prompt('Введите новое название для чата:', chatName);
            if (newName && newName.trim() !== '' && newName !== chatName) {
                await renameChatRequest(chatId, newName);
            }
        }
    };
    
    pinBtn.onclick = function(e) {
        e.stopPropagation();
        // Находим родительский элемент чата и закрываем меню
        const chatItem = document.querySelector(`[data-chat-id="${chatId}"]`);
        if (chatItem && chatItem.classList.contains('context-menu-open')) {
            chatItem.classList.remove('context-menu-open');
        }
        
        if (menu.parentNode) {
            menu.parentNode.removeChild(menu);
        }
        
        // TODO: Реализовать закрепление чата
        alert('Функция закрепления чата скоро будет доступна!');
    };
    
    deleteBtn.onclick = async function(e) {
        e.stopPropagation();
        
        // Находим родительский элемент чата и закрываем меню
        const chatItem = document.querySelector(`[data-chat-id="${chatId}"]`);
        if (chatItem && chatItem.classList.contains('context-menu-open')) {
            chatItem.classList.remove('context-menu-open');
        }
        
        if (menu.parentNode) {
            menu.parentNode.removeChild(menu);
        }
        
        // Определяем, активен ли удаляемый чат
        const isActive = chatItem && chatItem.classList.contains('active');
        
        // Используем кастомное модальное окно
        if (window.showDeleteConfirmation) {
            const confirmed = await window.showDeleteConfirmation(chatId, chatName, chatItem);
            if (confirmed) {
                // Отправляем запрос на удаление
                await deleteChatRequest(chatId, isActive);
            }
        } else {
            // Fallback на стандартный confirm если модальное окно не загружено
            if (confirm(`Вы уверены, что хотите удалить чат "${chatName}"?`)) {
                await deleteChatRequest(chatId, isActive);
            }
        }
    };
}

async function renameChatRequest(chatId, newName) {
    try {
        // Находим поле ввода для отправки данных
        const textarea = window.getChatInputField ? window.getChatInputField() : null;
        if (!textarea) {
            throw new Error('Не найдено поле для отправки данных');
        }
        
        // Отправляем специальный запрос на переименование
        // Формат: "rename:<chat_id>:<new_name>"
        const renameCommand = `rename:${chatId}:${encodeURIComponent(newName)}`;
        textarea.value = renameCommand;
        
        // Запускаем событие изменения
        try {
            const event = new Event('input', { 
                bubbles: true,
                cancelable: true 
            });
            textarea.dispatchEvent(event);
        } catch (e) {
            const changeEvent = new Event('change', {
                bubbles: true,
                cancelable: true
            });
            textarea.dispatchEvent(changeEvent);
        }
        
        // Обновляем список чатов через 500мс
        setTimeout(() => {
            if (window.chatListData && window.renderChatList) {
                window.renderChatList(window.chatListData);
            }
        }, 500);
        
    } catch (error) {
        console.error('Ошибка при переименовании:', error);
        alert('Не удалось переименовать чат. Попробуйте снова.');
    }
}

async function deleteChatRequest(chatId, isActive) {
    try {
        // Находим поле ввода для отправки ID чата
        const textarea = window.getChatInputField ? window.getChatInputField() : null;
        if (!textarea) {
            throw new Error('Не найдено поле для отправки данных');
        }
        
        // Отправляем специальный запрос на удаление
        // Формат: "delete:<chat_id>:<is_active>"
        const deleteCommand = `delete:${chatId}:${isActive ? 'active' : 'inactive'}`;
        textarea.value = deleteCommand;
        
        // Запускаем событие изменения
        try {
            const event = new Event('input', { 
                bubbles: true,
                cancelable: true 
            });
            textarea.dispatchEvent(event);
        } catch (e) {
            const changeEvent = new Event('change', {
                bubbles: true,
                cancelable: true
            });
            textarea.dispatchEvent(changeEvent);
        }
        
        // Обновляем список чатов через 500мс
        setTimeout(() => {
            if (window.chatListData && window.renderChatList) {
                window.renderChatList(window.chatListData);
            }
        }, 500);
        
    } catch (error) {
        console.error('Ошибка при удалении:', error);
        alert('Не удалось удалить чат. Попробуйте снова.');
    }
}

window.toggleContextMenu = function(chatItem, chatId, chatName) {
    if (!window.SELECTORS) return;
    
    // Проверяем, есть ли у этого элемента чата открытое меню
    if (chatItem.classList.contains('context-menu-open')) {
        // Находим и закрываем меню
        const menu = document.querySelector('.chat-context-menu.show[data-chat-id="' + chatId + '"]');
        if (menu && menu.parentNode) {
            menu.parentNode.removeChild(menu);
        }
        
        chatItem.classList.remove('context-menu-open');
        return;
    }
    
    // Закрываем все открытые меню и снимаем флаги
    document.querySelectorAll('.chat-item.context-menu-open').forEach(item => {
        item.classList.remove('context-menu-open');
    });
    
    // Закрываем все открытые меню
    if (window.closeAllContextMenus) {
        window.closeAllContextMenus();
    }
    
    // Создаем новое меню
    if (window.createContextMenu) {
        const menu = window.createContextMenu(chatId, chatName);
        
        // Добавляем меню в body для абсолютного позиционирования
        document.body.appendChild(menu);
        
        // Рассчитываем положение меню
        positionContextMenu(chatItem, menu);
        
        // Показываем меню
        menu.classList.add('show');
        
        // Помечаем элемент как имеющий открытое меню
        chatItem.classList.add('context-menu-open');
        
        // Закрываем меню при клике вне его
        setTimeout(() => {
            const closeMenuHandler = (e) => {
                // Если кликнули вне меню или на другой элемент управления
                if (!menu.contains(e.target) && 
                    !(chatItem.contains(e.target) && e.target.closest(SELECTORS.CHAT_CONTROL))) {
                    
                    // Удаляем класс с элемента
                    if (chatItem.classList.contains('context-menu-open')) {
                        chatItem.classList.remove('context-menu-open');
                    }
                    
                    // Закрываем меню
                    if (menu && menu.classList.contains('show')) {
                        menu.classList.remove('show');
                        if (menu.parentNode) {
                            menu.parentNode.removeChild(menu);
                        }
                    }
                    
                    document.removeEventListener('click', closeMenuHandler);
                }
            };
            document.addEventListener('click', closeMenuHandler);
        }, 10);
    }
};

function positionContextMenu(chatItem, menu) {
    if (!chatItem || !menu) return;
    
    // Показываем меню для получения размеров
    menu.style.display = 'block';
    menu.style.visibility = 'hidden';
    
    // Получаем размеры и позиции элементов
    const chatItemRect = chatItem.getBoundingClientRect();
    const menuRect = menu.getBoundingClientRect();
    const viewportHeight = window.innerHeight;
    const viewportWidth = window.innerWidth;
    
    // Рассчитываем позицию по умолчанию (справа от элемента)
    let topPosition = chatItemRect.top + (chatItemRect.height / 2) - (menuRect.height / 2);
    let leftPosition = chatItemRect.right + 10; // 10px справа от элемента
    
    // Проверяем, помещается ли меню справа
    if (leftPosition + menuRect.width > viewportWidth - 10) {
        // Если не помещается справа, показываем слева
        leftPosition = chatItemRect.left - menuRect.width - 10;
    }
    
    // Проверяем, помещается ли меню по вертикали
    if (topPosition + menuRect.height > viewportHeight - 10) {
        // Если не помещается снизу, сдвигаем вверх
        topPosition = viewportHeight - menuRect.height - 10;
    }
    
    if (topPosition < 10) {
        // Если не помещается сверху, сдвигаем вниз
        topPosition = 10;
    }
    
    // Устанавливаем позицию
    menu.style.position = 'fixed';
    menu.style.top = `${Math.max(10, topPosition)}px`;
    menu.style.left = `${Math.max(10, leftPosition)}px`;
    menu.style.right = 'auto';
    menu.style.bottom = 'auto';
    menu.style.visibility = 'visible';
    menu.style.zIndex = '10000'; // Высокий z-index чтобы было поверх всего
}