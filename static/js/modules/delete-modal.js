/* static/js/modules/delete-modal.js */
if (!window.SELECTORS) {
    console.error('SELECTORS не определены! Загрузите selectors.js первым');
}

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
        if (document.getElementById('deleteConfirmModal')) {
            this.modal = document.getElementById('deleteConfirmModal');
            this.message = document.getElementById('deleteModalMessage');
            this.cancelBtn = document.getElementById('cancelDeleteBtn');
            this.confirmBtn = document.getElementById('confirmDeleteBtn');
            return;
        }

        const modalHTML = `
            <div id="deleteConfirmModal" class="modal-overlay" style="display: none;">
                <div class="modal-container">
                    <div class="modal-header">
                        <h3 class="modal-title">Подтверждение удаления</h3>
                    </div>
                    <div class="modal-body">
                        <p id="deleteModalMessage" class="delete-modal-message"></p>
                    </div>
                    <div class="modal-footer">
                        <button class="modal-btn modal-btn-secondary" id="cancelDeleteBtn">Отмена</button>
                        <button class="modal-btn modal-btn-danger" id="confirmDeleteBtn">Удалить</button>
                    </div>
                </div>
            </div>
        `;

        const container = document.createElement('div');
        container.innerHTML = modalHTML;
        document.body.appendChild(container);

        this.modal = document.getElementById('deleteConfirmModal');
        this.message = document.getElementById('deleteModalMessage');
        this.cancelBtn = document.getElementById('cancelDeleteBtn');
        this.confirmBtn = document.getElementById('confirmDeleteBtn');

        this.attachEvents();
    }

    attachEvents() {
        this.cancelBtn.addEventListener('click', () => this.hide(false));
        this.confirmBtn.addEventListener('click', () => this.hide(true));

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

    show(chatId, chatName, chatItem) {
        return new Promise((resolve) => {
            this.currentChatId = chatId;
            this.currentChatName = chatName;
            this.currentChatItem = chatItem;
            this.resolvePromise = resolve;

            this.message.textContent = `Вы уверены, что хотите удалить чат "${chatName}"?`;
            this.modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
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

window.deleteConfirmationModal = new DeleteConfirmationModal();

window.showDeleteConfirmation = function(chatId, chatName, chatItem) {
    return window.deleteConfirmationModal.show(chatId, chatName, chatItem);
};