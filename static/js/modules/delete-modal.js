/* static/js/modules/modal.js - Кастомное модальное окно */

class DeleteConfirmationModal {
    constructor() {
        this.modal = null;
        this.message = null;
        this.cancelBtn = null;
        this.confirmBtn = null;
        this.currentChatId = null;
        this.currentChatName = null;
        this.currentChatItem = null;
        this.resolvePromise = null;
        
        this.init();
    }
    
    init() {
        // Создаем HTML структуру модального окна
        const modalHTML = `
            <div id="deleteConfirmModal" class="modal-overlay" style="display: none;">
                <div class="modal-container">
                    <div class="modal-header">
                        <h3 class="modal-title">Подтверждение удаления</h3>
                    </div>
                    <div class="modal-content">
                        <p id="deleteModalMessage">Вы уверены, что хотите удалить этот чат?</p>
                    </div>
                    <div class="modal-footer">
                        <button id="cancelDeleteBtn" class="modal-btn cancel-btn">Отмена</button>
                        <button id="confirmDeleteBtn" class="modal-btn delete-btn">Удалить</button>
                    </div>
                </div>
            </div>
        `;
        
        // Добавляем в DOM
        const container = document.createElement('div');
        container.innerHTML = modalHTML;
        document.body.appendChild(container);
        
        // Получаем элементы
        this.modal = document.getElementById('deleteConfirmModal');
        this.message = document.getElementById('deleteModalMessage');
        this.cancelBtn = document.getElementById('cancelDeleteBtn');
        this.confirmBtn = document.getElementById('confirmDeleteBtn');
        
        // Добавляем стили
        this.addStyles();
        
        // Назначаем обработчики
        this.cancelBtn.addEventListener('click', () => this.hide(false));
        this.confirmBtn.addEventListener('click', () => this.hide(true));
        
        // Закрытие по клику на оверлей
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide(false);
            }
        });
        
        // Закрытие по ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal.style.display !== 'none') {
                this.hide(false);
            }
        });
    }
    
    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .modal-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 99999;
                backdrop-filter: blur(4px);
                animation: modalFadeIn 0.2s ease;
            }
            
            .modal-container {
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
                width: 400px;
                max-width: 90vw;
                overflow: hidden;
                animation: modalSlideUp 0.3s ease;
            }
            
            .modal-header {
                padding: 24px 24px 16px 24px;
            }
            
            .modal-title {
                margin: 0;
                font-size: 18px;
                font-weight: 600;
                color: #111827;
            }
            
            .modal-content {
                padding: 0 24px 20px 24px;
                color: #374151;
                line-height: 1.5;
                font-size: 15px;
            }
            
            .modal-footer {
                padding: 0 24px 24px 24px;
                display: flex;
                justify-content: flex-end;
                gap: 12px;
                background: white;
            }
            
            .modal-btn {
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                border: none;
                transition: all 0.2s ease;
                min-width: 80px;
            }
            
            .modal-btn.cancel-btn {
                background: #f3f4f6;
                color: #374151;
                border: 1px solid #d1d5db;
            }
            
            .modal-btn.cancel-btn:hover {
                background: #e5e7eb;
                border-color: #9ca3af;
                transform: translateY(-1px);
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }
            
            .modal-btn.delete-btn {
                background: #dc2626;
                color: white;
            }
            
            .modal-btn.delete-btn:hover {
                background: #b91c1c;
                transform: translateY(-1px);
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }
            
            .modal-btn:active {
                transform: translateY(0);
                box-shadow: none;
            }
            
            .modal-btn:focus {
                outline: 2px solid #3b82f6;
                outline-offset: 2px;
            }
            
            @keyframes modalFadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            @keyframes modalSlideUp {
                from {
                    opacity: 0;
                    transform: translateY(20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            @media (max-width: 480px) {
                .modal-container {
                    width: 90vw;
                    margin: 16px;
                }
                
                .modal-header {
                    padding: 20px 20px 12px 20px;
                }
                
                .modal-content {
                    padding: 0 20px 16px 20px;
                    font-size: 14px;
                }
                
                .modal-footer {
                    padding: 0 20px 20px 20px;
                    flex-direction: row;
                    justify-content: flex-end;
                    gap: 8px;
                }
                
                .modal-btn {
                    min-width: 70px;
                    padding: 10px 16px;
                    font-size: 13px;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    show(chatId, chatName, chatItem) {
        return new Promise((resolve) => {
            this.currentChatId = chatId;
            this.currentChatName = chatName;
            this.currentChatItem = chatItem;
            this.resolvePromise = resolve;
            
            // Устанавливаем сообщение
            this.message.textContent = `Вы уверены, что хотите удалить чат "${chatName}"?`;
            
            // Показываем модальное окно
            this.modal.style.display = 'flex';
            document.body.style.overflow = 'hidden'; // Блокируем скролл
            
            // Фокусируем на кнопке Отмена для удобства
            this.cancelBtn.focus();
        });
    }
    
    hide(confirmed) {
        this.modal.style.display = 'none';
        document.body.style.overflow = '';
        
        if (this.resolvePromise) {
            this.resolvePromise(confirmed);
            this.resolvePromise = null;
        }
        
        this.currentChatId = null;
        this.currentChatName = null;
        this.currentChatItem = null;
    }
    
    isVisible() {
        return this.modal && this.modal.style.display !== 'none';
    }
}

// Создаем глобальный экземпляр
window.deleteConfirmationModal = new DeleteConfirmationModal();

// Функция для показа модального окна (для обратной совместимости)
window.showDeleteConfirmation = function(chatId, chatName, chatItem) {
    return window.deleteConfirmationModal.show(chatId, chatName, chatItem);
};