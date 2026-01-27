/* static/js/modules/context-menu.js */
import { closeAllContextMenus, activeContextMenu, SELECTORS } from './utils.js';
import { selectChat } from './main.js';

export function createContextMenu(chatId, chatName) {
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
}

function setupMenuHandlers(menu, chatId, chatName) {
    const renameBtn = menu.querySelector('.rename');
    const pinBtn = menu.querySelector('.pin');
    const deleteBtn = menu.querySelector('.delete');
    
    renameBtn.onclick = function(e) {
        e.stopPropagation();
        console.log('Переименовать чат:', chatId, chatName);
        closeAllContextMenus();
    };
    
    pinBtn.onclick = function(e) {
        e.stopPropagation();
        console.log('Закрепить чат:', chatId, chatName);
        closeAllContextMenus();
    };
    
    deleteBtn.onclick = async function(e) {
        e.stopPropagation();
        console.log('Удалить чат:', chatId, chatName);
        
        // Закрываем меню перед удалением
        closeAllContextMenus();
        
        // Показываем подтверждение
        if (confirm(`Вы уверены, что хотите удалить чат "${chatName}"?`)) {
            try {
                // Сначала переключаемся на этот чат (если он не активный)
                selectChat(chatId);
                
                // Ждем немного чтобы переключение произошло
                await new Promise(resolve => setTimeout(resolve, 100));
                
                // Находим и кликаем на кнопку удаления в сайдбаре
                const deleteBtnInSidebar = document.querySelector(SELECTORS.DELETE_BTN);
                if (deleteBtnInSidebar) {
                    deleteBtnInSidebar.click();
                    console.log('Запущено удаление чата через сайдбар');
                } else {
                    console.error('Кнопка удаления в сайдбаре не найдена');
                }
                
            } catch (error) {
                console.error('Ошибка при удалении чата:', error);
            }
        }
    };
}

export function toggleContextMenu(chatItem, chatId, chatName) {
    // Закрываем все открытые меню
    closeAllContextMenus();
    
    // Если кликнули на тот же элемент управления
    if (activeContextMenu && activeContextMenu.parentElement === chatItem) {
        window.activeContextMenu = null;
        return;
    }
    
    // Создаем и показываем новое меню
    const menu = createContextMenu(chatId, chatName);
    chatItem.appendChild(menu);
    menu.classList.add('show');
    window.activeContextMenu = menu;
    
    // Закрываем меню при клике вне его
    setTimeout(() => {
        const closeMenuHandler = (e) => {
            if (!menu.contains(e.target) && !chatItem.querySelector(SELECTORS.CHAT_CONTROL).contains(e.target)) {
                closeAllContextMenus();
                document.removeEventListener('click', closeMenuHandler);
            }
        };
        document.addEventListener('click', closeMenuHandler);
    }, 10);
}