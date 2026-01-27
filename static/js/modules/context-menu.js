/* static/js/modules/context-menu.js */
// Проверяем, что SELECTORS загружены
if (!window.SELECTORS) {
    console.error('SELECTORS не определены! Загрузите selectors.js первым');
}

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
    
    renameBtn.onclick = function(e) {
        e.stopPropagation();
        if (window.closeAllContextMenus) {
            window.closeAllContextMenus();
        }
        // TODO: Реализовать переименование через модальное окно
        const newName = prompt('Введите новое название для чата:', chatName);
        if (newName && newName.trim() !== '' && newName !== chatName) {
            // TODO: Вызов Python функции для переименования
        }
    };
    
    pinBtn.onclick = function(e) {
        e.stopPropagation();
        if (window.closeAllContextMenus) {
            window.closeAllContextMenus();
        }
        // TODO: Реализовать закрепление чата
    };
    
    deleteBtn.onclick = async function(e) {
        e.stopPropagation();
        
        // Закрываем меню перед удалением
        if (window.closeAllContextMenus) {
            window.closeAllContextMenus();
        }
        
        // Показываем подтверждение
        if (confirm(`Вы уверены, что хотите удалить чат "${chatName}"?`)) {
            try {
                // Определяем, активен ли удаляемый чат
                const chatItem = document.querySelector(`[data-chat-id="${chatId}"]`);
                const isActive = chatItem && chatItem.classList.contains('active');
                
                // Отправляем запрос на удаление
                await deleteChatRequest(chatId, isActive);
                
            } catch (error) {
                console.error('Ошибка при удалении чата:', error);
                alert('Ошибка при удалении чата. Пожалуйста, попробуйте снова.');
            }
        }
    };
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
        console.error('Ошибка при отправке запроса на удаление:', error);
        throw error;
    }
}

window.toggleContextMenu = function(chatItem, chatId, chatName) {
    if (!window.SELECTORS) return;
    
    // Закрываем все открытые меню
    if (window.closeAllContextMenus) {
        window.closeAllContextMenus();
    }
    
    // Если кликнули на тот же элемент управления, и меню уже открыто - закрываем его
    const existingMenu = chatItem.querySelector('.chat-context-menu.show');
    if (existingMenu) {
        existingMenu.classList.remove('show');
        // Удаляем меню из DOM после скрытия
        setTimeout(() => {
            if (existingMenu.parentNode) {
                existingMenu.parentNode.removeChild(existingMenu);
            }
        }, 150);
        window.activeContextMenu = null;
        return;
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
        window.activeContextMenu = menu;
        
        // Закрываем меню при клике вне его
        setTimeout(() => {
            const closeMenuHandler = (e) => {
                // Если кликнули вне меню или на другой элемент управления
                if (!menu.contains(e.target) && 
                    !(chatItem.contains(e.target) && e.target.closest(SELECTORS.CHAT_CONTROL))) {
                    if (window.closeAllContextMenus) {
                        window.closeAllContextMenus();
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