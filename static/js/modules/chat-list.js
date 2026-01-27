/* static/js/modules/chat-list.js */
// Проверяем, что SELECTORS загружены
if (!window.SELECTORS) {
    console.error('SELECTORS не определены! Загрузите selectors.js первым');
}

let chatListData = [];
let chatGroups = {};

window.renderChatList = function(chats) {
    if (!window.SELECTORS) return;
    
    const container = document.querySelector(window.SELECTORS.CHAT_LIST);
    if (!container) {
        setTimeout(() => window.renderChatList(chats), 50);
        return;
    }
    
    // Парсим данные если они пришли строкой
    if (typeof chats === 'string') {
        try {
            chats = JSON.parse(chats);
        } catch (e) {
            chats = { groups: {}, flat: [] };
        }
    }
    
    chatListData = chats.flat || [];
    chatGroups = chats.groups || {};
    
    container.innerHTML = '';
    
    // Если нет чатов
    if (!chatGroups || Object.keys(chatGroups).length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 20px; color: #64748b;">
                Нет чатов
            </div>
        `;
        return;
    }
    
    // Закрываем все открытые меню при обновлении списка
    if (window.closeAllContextMenus) {
        window.closeAllContextMenus();
    }
    
    // Отображаем группы в правильном порядке
    const groupOrder = ['Сегодня', 'Вчера', '7 дней', 'Месяц', 'Более месяца'];
    
    groupOrder.forEach(groupName => {
        if (chatGroups[groupName] && chatGroups[groupName].length > 0) {
            // Добавляем разделитель группы
            const divider = document.createElement('div');
            divider.className = 'group-divider';
            divider.textContent = groupName;
            container.appendChild(divider);
            
            // Добавляем чаты из этой группы
            chatGroups[groupName].forEach((chat) => {
                createChatElement(container, chat);
            });
        }
    });
    
    // Выделяем активный чат
    const activeChat = chatListData.find(chat => chat.is_current);
    if (activeChat && window.selectChat) {
        window.selectChat(activeChat.id);
    }
};

function createChatElement(container, chat) {
    if (!window.SELECTORS || !window.escapeHtml) return;
    
    const chatDiv = document.createElement('div');
    chatDiv.className = 'chat-item';
    chatDiv.setAttribute('data-chat-id', chat.id);
    
    // Структура с элементом управления
    chatDiv.innerHTML = `
        <div class="chat-name-wrapper">
            <div class="chat-name">${window.escapeHtml(chat.name)}</div>
        </div>
        <div class="chat-control"></div>
    `;
    
    if (chat.is_current) {
        chatDiv.classList.add('active');
    }
    
    // Клик на весь элемент чата
    chatDiv.onclick = function(e) {
        if (!window.SELECTORS) return;
        
        // Если кликнули на элемент управления или контекстное меню - не переключаем чат
        if (e.target.classList.contains(window.SELECTORS.CHAT_CONTROL.replace('.', '')) || 
            e.target.closest(window.SELECTORS.CHAT_CONTROL) ||
            e.target.classList.contains(window.SELECTORS.CONTEXT_MENU_ITEM.replace('.', '')) ||
            e.target.closest(window.SELECTORS.CONTEXT_MENU)) {
            e.stopPropagation();
            return;
        }
        const chatId = this.getAttribute('data-chat-id');
        if (window.selectChat) {
            window.selectChat(chatId);
        }
        if (window.closeAllContextMenus) {
            window.closeAllContextMenus();
        }
    };
    
    // Обработчик для элемента управления
    const controlBtn = chatDiv.querySelector(window.SELECTORS.CHAT_CONTROL);
    controlBtn.onclick = function(e) {
        e.stopPropagation();
        // Динамически загружаем модуль контекстного меню
        if (window.toggleContextMenu) {
            window.toggleContextMenu(chatDiv, chat.id, chat.name);
        }
    };
    
    container.appendChild(chatDiv);
}