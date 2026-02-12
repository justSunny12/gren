/* static/js/modules/rename-modal.js */
if (!window.SELECTORS) {
    console.error('SELECTORS не определены! Загрузите selectors.js первым');
}

class RenameChatModal {
    constructor() {
        this.modal = null;
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
        if (document.getElementById('renameChatModal')) {
            this.modal = document.getElementById('renameChatModal');
            this.input = document.getElementById('renameChatInput');
            this.message = document.getElementById('renameModalMessage');
            this.cancelBtn = document.getElementById('cancelRenameBtn');
            this.confirmBtn = document.getElementById('confirmRenameBtn');
            this.charCounter = document.getElementById('renameCharCounter');
            return;
        }

        const modalHTML = `
            <div id="renameChatModal" class="modal-overlay" style="display: none;">
                <div class="modal-container">
                    <div class="modal-header">
                        <h3 class="modal-title">Переименовать чат</h3>
                    </div>
                    <div class="modal-body">
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
                    </div>
                    <div class="modal-footer">
                        <button class="modal-btn modal-btn-secondary" id="cancelRenameBtn">Отмена</button>
                        <button class="modal-btn modal-btn-primary" id="confirmRenameBtn">Сохранить</button>
                    </div>
                </div>
            </div>
        `;

        const container = document.createElement('div');
        container.innerHTML = modalHTML;
        document.body.appendChild(container);

        this.modal = document.getElementById('renameChatModal');
        this.input = document.getElementById('renameChatInput');
        this.message = document.getElementById('renameModalMessage');
        this.cancelBtn = document.getElementById('cancelRenameBtn');
        this.confirmBtn = document.getElementById('confirmRenameBtn');
        this.charCounter = document.getElementById('renameCharCounter');

        this.attachEvents();
    }

    attachEvents() {
        this.cancelBtn.addEventListener('click', () => this.hide(false));
        this.confirmBtn.addEventListener('click', () => this.handleConfirm());
        this.input.addEventListener('keyup', (e) => this.handleInputKeyup(e));
        this.input.addEventListener('input', () => this.updateCharCounter());

        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide(false);
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal.style.display !== 'none') {
                this.hide(false);
            }
        });
    }

    show(chatId, chatName) {
        return new Promise((resolve) => {
            this.currentChatId = chatId;
            this.currentChatName = chatName;
            this.resolvePromise = resolve;

            this.input.value = chatName;
            this.input.classList.remove('input-error');
            this.message.textContent = '';
            this.message.className = 'rename-modal-message';
            this.updateCharCounter();
            this.confirmBtn.disabled = chatName.trim() === '';

            this.modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';

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
            this.confirmBtn.disabled = this.input.value.trim() === '';
        }
    }

    updateCharCounter() {
        const length = this.input.value.length;
        this.charCounter.textContent = `${length}/50`;
        this.charCounter.className = 'rename-char-counter';
        if (length >= 45 && length <= 50) {
            this.charCounter.classList.add('near-limit');
            this.clearError();
        } else if (length > 50) {
            this.charCounter.classList.add('over-limit');
            this.showError('Превышен лимит в 50 символов');
        } else {
            this.clearError();
        }
    }

    showError(message) {
        this.input.classList.add('input-error');
        this.message.textContent = message;
        this.message.classList.add('message-error');
    }

    clearError() {
        this.input.classList.remove('input-error');
        this.message.textContent = '';
        this.message.className = 'rename-modal-message';
    }

    isVisible() {
        return this.modal && this.modal.style.display !== 'none';
    }
}

window.renameChatModal = new RenameChatModal();

window.showRenameChatModal = function(chatId, chatName) {
    return window.renameChatModal.show(chatId, chatName);
};