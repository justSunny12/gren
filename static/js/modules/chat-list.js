/* static/js/modules/chat-list.js */
import { SELECTORS, SWITCH_DEBOUNCE_MS, closeAllContextMenus } from './utils.js';
import { selectChat } from './main.js';

let chatListData = [];
let chatGroups = {};

export function renderChatList(chats) {
    const container = document.querySelector(SELECTORS.CHAT_LIST);
    if (!container) {
        setTimeout(() => renderChatList(chats), 50);
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
    closeAllContextMenus();
    
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
    if (activeChat) {
        selectChat(activeChat.id);
    }
}

function createChatElement(container, chat) {
    const chatDiv = document.createElement('div');
    chatDiv.className = 'chat-item';
    chatDiv.setAttribute('data-chat-id', chat.id);
    
    // Структура с элементом управления
    chatDiv.innerHTML = `
        <div class="chat-name-wrapper">
            <div class="chat-name">${escapeHtml(chat.name)}</div>
        </div>
        <div class="chat-control"></div>
    `;
    
    if (chat.is_current) {
        chatDiv.classList.add('active');
    }
    
    // Клик на весь элемент чата
    chatDiv.onclick = function(e) {
        // Если кликнули на элемент управления или контекстное меню - не переключаем чат
        if (e.target.classList.contains(SELECTORS.CHAT_CONTROL.replace('.', '')) || 
            e.target.closest(SELECTORS.CHAT_CONTROL) ||
            e.target.classList.contains(SELECTORS.CONTEXT_MENU_ITEM.replace('.', '')) ||
            e.target.closest(SELECTORS.CONTEXT_MENU)) {
            e.stopPropagation();
            return;
        }
        const chatId = this.getAttribute('data-chat-id');
        selectChat(chatId);
        closeAllContextMenus();
    };
    
    // Обработчик для элемента управления
    const controlBtn = chatDiv.querySelector(SELECTORS.CHAT_CONTROL);
    controlBtn.onclick = function(e) {
        e.stopPropagation();
        import('./context-menu.js').then(module => {
            module.toggleContextMenu(chatDiv, chat.id, chat.name);
        });
    };
    
    container.appendChild(chatDiv);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

export { chatListData, chatGroups };