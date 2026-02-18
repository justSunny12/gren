/* static/js/modules/chat-list.js */
if (!window.SELECTORS) {
    console.error('SELECTORS не определены! Загрузите selectors.js первым');
}

let chatListData = [];
let chatGroups = {};

/**
 * Только визуальное выделение активного чата (без отправки события в Gradio)
 */
window.setActiveChatClass = function(chatId) {
    if (!window.SELECTORS) return;
    
    document.querySelectorAll(window.SELECTORS.CHAT_ITEM).forEach(el => {
        el.classList.remove('active');
    });
    
    const active = document.querySelector(`[data-chat-id="${chatId}"]`);
    if (active) {
        active.classList.add('active');
    }
};

/**
 * Рендерит список чатов
 * @param {Object|string} chats - данные чатов
 * @param {string} scrollTarget - 'top', 'today' или 'none'
 */
window.renderChatList = function(chats, scrollTarget = 'none') {
    if (!window.SELECTORS) return;
    const container = document.querySelector(window.SELECTORS.CHAT_LIST);
    if (!container) {
        setTimeout(() => window.renderChatList(chats, scrollTarget), 50);
        return;
    }

    if (typeof chats === 'string') {
        try {
            chats = JSON.parse(chats);
        } catch (e) {
            console.error('Ошибка парсинга JSON:', e);
            chats = { groups: {}, flat: [] };
        }
    }

    // ДИАГНОСТИКА
    console.log('📋 renderChatList: _thinking_state =', chats._thinking_state, '_search_state =', chats._search_state);

    chatListData = chats.flat || [];
    chatGroups = chats.groups || {};

    container.innerHTML = '';

    if (!chatGroups || Object.keys(chatGroups).length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 20px; color: #64748b;">Нет чатов</div>';
        return;
    }

    if (window.closeAllContextMenus) window.closeAllContextMenus();

    const groupOrder = ['Закрепленные', 'Сегодня', 'Вчера', '7 дней', 'Месяц', 'Более месяца'];

    groupOrder.forEach(groupName => {
        if (chatGroups[groupName] && chatGroups[groupName].length > 0) {
            const divider = document.createElement('div');
            divider.className = 'group-divider';
            divider.textContent = groupName;
            container.appendChild(divider);

            chatGroups[groupName].forEach(chat => {
                createChatElement(container, chat);
            });
        }
    });

    // Скролл
    let target = scrollTarget;
    if (chats && typeof chats === 'object' && chats._scroll_target !== undefined) {
        target = chats._scroll_target;
    }
    if (target === 'top') {
        requestAnimationFrame(() => {
            const scrollContainer = document.querySelector('.chat-list') || document.querySelector(window.SELECTORS.CHAT_LIST);
            if (scrollContainer) scrollContainer.scrollTop = 0;
        });
    } else if (target === 'today') {
        requestAnimationFrame(() => {
            const scrollContainer = document.querySelector('.chat-list') || document.querySelector(window.SELECTORS.CHAT_LIST);
            if (!scrollContainer) return;
            const todayHeader = Array.from(document.querySelectorAll('.group-divider')).find(
                el => el.textContent.trim() === 'Сегодня'
            );
            if (todayHeader) todayHeader.scrollIntoView({ behavior: 'smooth', block: 'start' });
            else scrollContainer.scrollTop = 0;
        });
    }

    // Установка состояния кнопки мышления
    if (chats && typeof chats === 'object' && chats._thinking_state !== undefined) {
        if (window.setThinkingButtonState) {
            window.setThinkingButtonState(chats._thinking_state);
        }
    }

    // Установка состояния кнопки поиска
    if (chats && typeof chats === 'object' && chats._search_state !== undefined) {
        if (window.setSearchButtonState) {
            window.setSearchButtonState(chats._search_state);
        }
    }

    // Выделение активного чата и фокус
    const activeChat = chatListData.find(chat => chat.is_current);
    if (activeChat) {
        window.setActiveChatClass(activeChat.id);
        if (!window.isGenerating) {
            setTimeout(() => {
                const inputField = document.querySelector('.chat-input-wrapper textarea');
                if (inputField && !inputField.disabled) inputField.focus();
            }, 10);
        }
    }
};

function createChatElement(container, chat) {
    if (!window.SELECTORS || !window.escapeHtml) return;
    
    const chatDiv = document.createElement('div');
    chatDiv.className = 'chat-item';
    chatDiv.setAttribute('data-chat-id', chat.id);
    
    chatDiv.innerHTML = `
        <div class="chat-name-wrapper">
            <div class="chat-name">${window.escapeHtml(chat.name)}</div>
        </div>
        <div class="chat-control"></div>
    `;
    
    if (chat.is_current) {
        chatDiv.classList.add('active');
    }
    
    chatDiv.onclick = function(e) {
        if (!window.SELECTORS) return;
        
        if (e.target.classList.contains(window.SELECTORS.CHAT_CONTROL.replace('.', '')) || 
            e.target.closest(window.SELECTORS.CHAT_CONTROL) ||
            e.target.classList.contains(window.SELECTORS.CONTEXT_MENU_ITEM.replace('.', '')) ||
            e.target.closest(window.SELECTORS.CONTEXT_MENU)) {
            e.stopPropagation();
            return;
        }
        
        if (window.closeAllContextMenus) {
            window.closeAllContextMenus();
        }
        
        const chatId = this.getAttribute('data-chat-id');
        if (window.selectChat) {
            window.selectChat(chatId);
        }
    };
    
    const controlBtn = chatDiv.querySelector(window.SELECTORS.CHAT_CONTROL);
    controlBtn.onclick = function(e) {
        e.stopPropagation();
        if (window.toggleContextMenu) {
            window.toggleContextMenu(chatDiv, chat.id, chat.name, chat.pinned || false);
        }
    };
    
    container.appendChild(chatDiv);
}