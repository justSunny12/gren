/* static/js/modules/rename-modal.js - Модальное окно переименования */

class RenameChatModal {
    constructor() {
        this.modal = null;
        this.title = null;
        this.input = null;
        this.message = null;
        this.cancelBtn = null;
        this.confirmBtn = null;
        this.charCounter = null;
        this.currentChatId = null;
        this.currentChatName = null;
        this.resolvePromise = null;
        
        this.init();
    }
    
    init() {
        // Создаем HTML структуру модального окна с уникальными классами
        const modalHTML = `
            <div id="renameChatModal" class="rename-modal-overlay" style="display: none;">
                <div class="rename-modal-container">
                    <div class="rename-modal-header">
                        <h3 class="rename-modal-title">Переименовать чат</h3>
                    </div>
                    <div class="rename-modal-body">
                        <div class="rename-input-container">
                            <div class="rename-input-with-counter">
                                <input type="text" 
                                       id="renameChatInput" 
                                       class="rename-modal-input" 
                                       placeholder="Введите новое название" 
                                       maxlength="50">
                                <div class="rename-char-counter" id="renameCharCounter">0/50</div>
                            </div>
                            <div id="renameModalMessage" class="rename-modal-message"></div>
                        </div>
                        <div class="rename-modal-footer">
                            <button id="cancelRenameBtn" class="rename-modal-btn rename-cancel-btn">Отмена</button>
                            <button id="confirmRenameBtn" class="rename-modal-btn rename-confirm-btn">Сохранить</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Добавляем в DOM
        const container = document.createElement('div');
        container.innerHTML = modalHTML;
        document.body.appendChild(container);
        
        // Получаем элементы
        this.modal = document.getElementById('renameChatModal');
        this.title = document.querySelector('.rename-modal-title');
        this.input = document.getElementById('renameChatInput');
        this.message = document.getElementById('renameModalMessage');
        this.cancelBtn = document.getElementById('cancelRenameBtn');
        this.confirmBtn = document.getElementById('confirmRenameBtn');
        this.charCounter = document.getElementById('renameCharCounter');
        
        // Добавляем стили с уникальными классами
        this.addStyles();
        
        // Назначаем обработчики
        this.cancelBtn.addEventListener('click', () => this.hide(false));
        this.confirmBtn.addEventListener('click', () => this.handleConfirm());
        this.input.addEventListener('keyup', (e) => this.handleInputKeyup(e));
        this.input.addEventListener('input', () => this.updateCharCounter());
        this.input.addEventListener('focus', () => this.updateCharCounter());
        this.input.addEventListener('blur', () => this.updateCharCounter());
        
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
        // Проверяем, не добавлены ли уже стили
        if (document.getElementById('rename-modal-styles')) {
            return;
        }
        
        const style = document.createElement('style');
        style.id = 'rename-modal-styles';
        style.textContent = `
            /* Стили для модального окна переименования */
            .rename-modal-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
                animation: rename-modal-fade-in 0.15s ease;
            }
            
            .rename-modal-container {
                background: white;
                border-radius: 10px;
                box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
                overflow: hidden;
                animation: rename-modal-slide-up 0.15s ease-out;
                max-width: 420px;
                min-width: 320px;
                width: 100%;
            }
            
            .rename-modal-header {
                padding: 18px 20px 12px 20px;
            }
            
            .rename-modal-title {
                margin: 0;
                font-size: 17px;
                font-weight: 600;
                color: #111827;
            }
            
            .rename-modal-body {
                padding: 0 20px 20px 20px;
            }
            
            .rename-input-container {
                position: relative;
                margin-bottom: 4px;
            }
            
            .rename-input-with-counter {
                position: relative;
                display: flex;
                align-items: center;
                margin-bottom: 2px;
            }
            
            .rename-modal-input {
                width: 100%;
                padding: 9px 65px 9px 12px;
                font-size: 14px;
                border: 1.5px solid #e5e7eb;
                border-radius: 6px;
                transition: all 0.12s ease;
                box-sizing: border-box;
                font-family: inherit;
                line-height: 1.4;
                height: 40px;
                background: #fafafa;
            }
            
            .rename-modal-input:focus {
                outline: none;
                border-color: #3b82f6;
                background: white;
                box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
            }
            
            .rename-modal-input.rename-input-error {
                border-color: #dc2626;
                background: white;
            }
            
            .rename-modal-input.rename-input-error:focus {
                border-color: #dc2626;
                box-shadow: 0 0 0 2px rgba(220, 38, 38, 0.1);
            }
            
            .rename-char-counter {
                position: absolute;
                right: 10px;
                top: 50%;
                transform: translateY(-50%);
                font-size: 11px;
                color: #9ca3af;
                background: transparent;
                padding: 0 6px;
                transition: all 0.12s ease;
                pointer-events: none;
                user-select: none;
                font-weight: 500;
                letter-spacing: -0.05px;
            }
            
            .rename-modal-input:focus + .rename-char-counter {
                color: #6b7280;
            }
            
            .rename-modal-input.rename-input-error + .rename-char-counter {
                color: #dc2626;
            }
            
            .rename-char-counter.rename-near-limit {
                color: #f59e0b;
                font-weight: 600;
            }
            
            .rename-modal-input:focus + .rename-char-counter.rename-near-limit {
                color: #d97706;
            }
            
            .rename-char-counter.rename-over-limit {
                color: #dc2626;
                font-weight: 600;
            }
            
            .rename-modal-input:focus + .rename-char-counter.rename-over-limit {
                color: #b91c1c;
            }
            
            .rename-modal-message {
                margin-top: 2px;
                margin-bottom: 12px;
                font-size: 12px;
                min-height: 14px;
                padding-left: 2px;
                line-height: 1.3;
            }
            
            .rename-modal-message.rename-message-error {
                color: #dc2626;
            }
            
            .rename-modal-message.rename-message-success {
                color: #059669;
            }
            
            .rename-modal-footer {
                display: flex;
                justify-content: flex-end;
                gap: 10px;
                padding: 0;
                margin-top: 0;
                background: white;
            }
            
            .rename-modal-btn {
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
                cursor: pointer;
                border: none;
                transition: all 0.12s ease;
                min-width: 70px;
                height: 32px;
                line-height: 1;
            }
            
            .rename-modal-btn.rename-cancel-btn {
                background: #f3f4f6;
                color: #374151;
                border: 1px solid #d1d5db;
            }
            
            .rename-modal-btn.rename-cancel-btn:hover {
                background: #e5e7eb;
                border-color: #9ca3af;
                transform: translateY(-1px);
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
            }
            
            .rename-modal-btn.rename-confirm-btn {
                background: #3b82f6;
                color: white;
            }
            
            .rename-modal-btn.rename-confirm-btn:hover {
                background: #2563eb;
                transform: translateY(-1px);
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
            }
            
            .rename-modal-btn.rename-confirm-btn:disabled {
                background: #9ca3af;
                cursor: not-allowed;
                transform: none;
                box-shadow: none;
            }
            
            .rename-modal-btn.rename-confirm-btn:disabled:hover {
                background: #9ca3af;
                transform: none;
                box-shadow: none;
            }
            
            @keyframes rename-modal-fade-in {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            @keyframes rename-modal-slide-up {
                from {
                    opacity: 0;
                    transform: translateY(10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            @media (max-width: 480px) {
                .rename-modal-container {
                    max-width: 90vw;
                    min-width: unset;
                    width: 300px;
                }
                
                .rename-modal-header {
                    padding: 16px 18px 10px 18px;
                }
                
                .rename-modal-body {
                    padding: 0 18px 18px 18px;
                }
                
                .rename-modal-footer {
                    gap: 8px;
                }
                
                .rename-modal-btn {
                    min-width: 65px;
                    padding: 7px 14px;
                    font-size: 12.5px;
                    height: 30px;
                }
                
                .rename-modal-input {
                    font-size: 13.5px;
                    padding: 8px 58px 8px 10px;
                    height: 38px;
                }
                
                .rename-char-counter {
                    right: 8px;
                    font-size: 10.5px;
                    padding: 0 5px;
                }
                
                .rename-modal-message {
                    font-size: 11.5px;
                    margin-bottom: 10px;
                }
                
                .rename-modal-title {
                    font-size: 16px;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    show(chatId, chatName) {
        return new Promise((resolve) => {
            this.currentChatId = chatId;
            this.currentChatName = chatName;
            this.resolvePromise = resolve;
            
            // Устанавливаем текущее название в поле ввода
            this.input.value = chatName;
            
            // Сбрасываем состояние
            this.input.classList.remove('rename-input-error');
            this.message.textContent = '';
            this.message.className = 'rename-modal-message';
            
            // Обновляем счетчик символов
            this.updateCharCounter();
            
            // Включаем кнопку сохранения если есть текст
            this.confirmBtn.disabled = chatName.trim() === '';
            
            // Показываем модальное окно
            this.modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
            
            // Фокусируем на поле ввода и выделяем текст
            setTimeout(() => {
                this.input.focus();
                this.input.select();
            }, 30);
        });
    }
    
    hide(confirmed, newName = null) {
        this.modal.style.display = 'none';
        document.body.style.overflow = '';
        
        if (this.resolvePromise) {
            this.resolvePromise(confirmed ? newName : null);
            this.resolvePromise = null;
        }
        
        this.currentChatId = null;
        this.currentChatName = null;
    }
    
    handleConfirm() {
        const newName = this.input.value.trim();
        
        // Валидация
        if (!newName) {
            this.showError('Введите название чата');
            this.input.focus();
            return;
        }
        
        if (newName === this.currentChatName) {
            this.hide(false);
            return;
        }
        
        if (newName.length > 50) {
            this.showError('Название не должно превышать 50 символов');
            return;
        }
        
        this.hide(true, newName);
    }
    
    handleInputKeyup(e) {
        if (e.key === 'Enter') {
            this.handleConfirm();
        } else if (e.key === 'Escape') {
            this.hide(false);
        } else {
            // Включаем/выключаем кнопку сохранения
            this.confirmBtn.disabled = this.input.value.trim() === '';
        }
    }
    
    updateCharCounter() {
        const length = this.input.value.length;
        this.charCounter.textContent = `${length}/50`;
        
        // Обновляем классы в зависимости от длины
        this.charCounter.className = 'rename-char-counter';
        
        if (length >= 45 && length <= 50) {
            this.charCounter.classList.add('rename-near-limit');
            this.clearError();
        } else if (length > 50) {
            this.charCounter.classList.add('rename-over-limit');
            this.showError('Превышен лимит в 50 символов');
        } else {
            this.clearError();
        }
    }
    
    showError(message) {
        this.input.classList.add('rename-input-error');
        this.message.textContent = message;
        this.message.classList.add('rename-message-error');
    }
    
    clearError() {
        this.input.classList.remove('rename-input-error');
        this.message.textContent = '';
        this.message.className = 'rename-modal-message';
    }
    
    isVisible() {
        return this.modal && this.modal.style.display !== 'none';
    }
}

// Создаем глобальный экземпляр
window.renameChatModal = new RenameChatModal();

// Функция для показа модального окна
window.showRenameChatModal = function(chatId, chatName) {
    return window.renameChatModal.show(chatId, chatName);
};