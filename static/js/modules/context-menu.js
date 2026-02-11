/* static/js/modules/context-menu.js */
// Проверяем, что SELECTORS загружены
if (!window.SELECTORS) {
    console.error('SELECTORS не определены! Загрузите selectors.js первым');
}

window.createContextMenu = function(chatId, chatName, isPinned) {
    if (!window.SELECTORS) return null;
    
    const menu = document.createElement('div');
    menu.className = 'chat-context-menu';
    menu.setAttribute('data-chat-id', chatId);
    
    const pinText = isPinned ? "Открепить" : "Закрепить";
    const pinIcon = isPinned ? `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 17v5"/>
            <path d="M15 9.34V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H7.89"/>
            <path d="m2 2 20 20"/>
            <path d="M9 9v1.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h11"/>
        </svg>
    ` : `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 17v5"/>
            <path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z"/>
        </svg>
    `;
    
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
                ${pinIcon}
            </span>
            <span>${pinText}</span>
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
    
    setupMenuHandlers(menu, chatId, chatName, isPinned);
    return menu;
};

function setupMenuHandlers(menu, chatId, chatName, isPinned) {
    const renameBtn = menu.querySelector('.rename');
    const pinBtn = menu.querySelector('.pin');
    const deleteBtn = menu.querySelector('.delete');
    
    renameBtn.onclick = async function(e) {
        e.stopPropagation();
        closeMenuAndCleanup(menu, chatId);
        
        if (window.showRenameChatModal) {
            const newName = await window.showRenameChatModal(chatId, chatName);
            if (newName && newName !== chatName) {
                await renameChatRequest(chatId, newName);
            }
        } else {
            const newName = prompt('Введите новое название для чата:', chatName);
            if (newName && newName.trim() !== '' && newName !== chatName) {
                await renameChatRequest(chatId, newName);
            }
        }
    };
    
    pinBtn.onclick = function(e) {
        e.stopPropagation();
        closeMenuAndCleanup(menu, chatId);
        const action = isPinned ? 'unpin' : 'pin';
        pinChatRequest(chatId, action);
    };
    
    deleteBtn.onclick = async function(e) {
        e.stopPropagation();
        const chatItem = document.querySelector(`[data-chat-id="${chatId}"]`);
        const isActive = chatItem?.classList.contains('active') || false;
        closeMenuAndCleanup(menu, chatId);
        
        if (window.showDeleteConfirmation) {
            const confirmed = await window.showDeleteConfirmation(chatId, chatName, chatItem);
            if (confirmed) {
                await deleteChatRequest(chatId, isActive);
            }
        } else {
            if (confirm(`Вы уверены, что хотите удалить чат "${chatName}"?`)) {
                await deleteChatRequest(chatId, isActive);
            }
        }
    };
}

function closeMenuAndCleanup(menu, chatId) {
    const chatItem = document.querySelector(`[data-chat-id="${chatId}"]`);
    if (chatItem?.classList.contains('context-menu-open')) {
        chatItem.classList.remove('context-menu-open');
    }
    if (menu.parentNode) {
        menu.parentNode.removeChild(menu);
    }
}

async function renameChatRequest(chatId, newName) {
    try {
        const textarea = window.getChatInputField?.();
        if (!textarea) throw new Error('Не найдено поле для отправки данных');
        
        textarea.value = `rename:${chatId}:${encodeURIComponent(newName)}`;
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
    } catch (error) {
        console.error('Ошибка при переименовании:', error);
        alert('Не удалось переименовать чат. Попробуйте снова.');
    }
}

async function pinChatRequest(chatId, action) {
    try {
        const textarea = window.getChatInputField?.();
        if (!textarea) throw new Error('Не найдено поле для отправки данных');
        
        textarea.value = `${action}:${chatId}:${action}`;
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
    } catch (error) {
        console.error('Ошибка при закреплении/откреплении:', error);
        alert('Не удалось закрепить/открепить чат. Попробуйте снова.');
    }
}

async function deleteChatRequest(chatId, isActive) {
    try {
        const textarea = window.getChatInputField?.();
        if (!textarea) throw new Error('Не найдено поле для отправки данных');
        
        textarea.value = `delete:${chatId}:${isActive ? 'active' : 'inactive'}`;
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
    } catch (error) {
        console.error('Ошибка при удалении:', error);
        alert('Не удалось удалить чат. Попробуйте снова.');
    }
}

window.toggleContextMenu = function(chatItem, chatId, chatName, isPinned) {
    if (!window.SELECTORS) return;
    
    if (chatItem.classList.contains('context-menu-open')) {
        const menu = document.querySelector(`.chat-context-menu.show[data-chat-id="${chatId}"]`);
        menu?.parentNode?.removeChild(menu);
        chatItem.classList.remove('context-menu-open');
        return;
    }
    
    document.querySelectorAll('.chat-item.context-menu-open').forEach(item => {
        item.classList.remove('context-menu-open');
    });
    
    window.closeAllContextMenus?.();
    
    const menu = window.createContextMenu?.(chatId, chatName, isPinned);
    if (!menu) return;
    
    document.body.appendChild(menu);
    positionContextMenu(chatItem, menu);
    menu.classList.add('show');
    chatItem.classList.add('context-menu-open');
    
    setTimeout(() => {
        const closeMenuHandler = (e) => {
            if (!menu.contains(e.target) && 
                !(chatItem.contains(e.target) && e.target.closest(window.SELECTORS.CHAT_CONTROL))) {
                
                chatItem.classList.remove('context-menu-open');
                menu.classList.remove('show');
                menu.parentNode?.removeChild(menu);
                document.removeEventListener('click', closeMenuHandler);
            }
        };
        document.addEventListener('click', closeMenuHandler);
    }, 10);
};

function positionContextMenu(chatItem, menu) {
    menu.style.display = 'block';
    menu.style.visibility = 'hidden';
    
    const chatRect = chatItem.getBoundingClientRect();
    const menuRect = menu.getBoundingClientRect();
    const vh = window.innerHeight;
    const vw = window.innerWidth;
    
    let top = chatRect.top + (chatRect.height - menuRect.height) / 2;
    let left = chatRect.right + 10;
    
    if (left + menuRect.width > vw - 10) left = chatRect.left - menuRect.width - 10;
    if (top + menuRect.height > vh - 10) top = vh - menuRect.height - 10;
    if (top < 10) top = 10;
    
    Object.assign(menu.style, {
        position: 'fixed',
        top: `${Math.max(10, top)}px`,
        left: `${Math.max(10, left)}px`,
        right: 'auto',
        bottom: 'auto',
        visibility: 'visible',
        zIndex: '10000'
    });
}