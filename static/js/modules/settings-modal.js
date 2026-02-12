/* static/js/modules/settings-modal.js */
if (!window.SELECTORS) {
    console.error('SELECTORS не определены! Загрузите selectors.js первым');
}

class SettingsModal {
    constructor() {
        this.modalId = 'settingsModal';
        this.modal = null;
        this.currentSettings = null;

        // Храним дефолтные значения отдельно
        this.defaultMaxTokens = 2048;
        this.defaultTemperature = 0.7;

        this.init();
    }

    // Создаёт HTML модального окна (один раз)
    createModal() {
        if (document.getElementById(this.modalId)) {
            return;
        }

        const modalHTML = `
            <div id="${this.modalId}" class="modal-overlay" style="display: none;">
                <div class="modal-container">
                    <div class="modal-header">
                        <h3 class="modal-title">Параметры генерации</h3>
                    </div>
                    <div class="modal-body">
                        <div class="settings-section">
                            <div class="settings-label">
                                <span>Максимум токенов</span>
                                <span class="settings-value" id="maxTokensValue">2048</span>
                            </div>
                            <div class="settings-slider-wrapper">
                                <input type="range" 
                                       id="maxTokensSlider" 
                                       class="settings-slider" 
                                       min="64" max="4096" step="64" 
                                       value="2048">
                                <button class="settings-reset-btn" id="resetMaxTokensBtn" title="Сбросить к стандартному">↺</button>
                            </div>
                        </div>
                        <div class="settings-section">
                            <div class="settings-label">
                                <span>Температура</span>
                                <span class="settings-value" id="temperatureValue">0.7</span>
                            </div>
                            <div class="settings-slider-wrapper">
                                <input type="range" 
                                       id="temperatureSlider" 
                                       class="settings-slider" 
                                       min="0.1" max="1.5" step="0.05" 
                                       value="0.7">
                                <button class="settings-reset-btn" id="resetTemperatureBtn" title="Сбросить к стандартному">↺</button>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="modal-btn modal-btn-secondary" id="cancelSettingsBtn">Отмена</button>
                        <button class="modal-btn modal-btn-primary" id="applySettingsBtn">Применить</button>
                    </div>
                </div>
            </div>
        `;

        const container = document.createElement('div');
        container.innerHTML = modalHTML;
        document.body.appendChild(container);
    }

    // Обновляет ссылки на DOM-элементы (перед каждым показом)
    refreshElements() {
        this.modal = document.getElementById(this.modalId);
        this.maxTokensSlider = document.getElementById('maxTokensSlider');
        this.temperatureSlider = document.getElementById('temperatureSlider');
        this.maxTokensValue = document.getElementById('maxTokensValue');
        this.temperatureValue = document.getElementById('temperatureValue');
        this.resetMaxTokensBtn = document.getElementById('resetMaxTokensBtn');
        this.resetTemperatureBtn = document.getElementById('resetTemperatureBtn');
        this.cancelBtn = document.getElementById('cancelSettingsBtn');
        this.applyBtn = document.getElementById('applySettingsBtn');
    }

    // Привязывает обработчики событий (удаляет старые, добавляет новые)
    attachEvents() {
        // Удаляем старые обработчики
        if (this.maxTokensSlider) {
            this.maxTokensSlider.removeEventListener('input', this.maxTokensInputHandler);
        }
        if (this.temperatureSlider) {
            this.temperatureSlider.removeEventListener('input', this.temperatureInputHandler);
        }
        if (this.resetMaxTokensBtn) {
            this.resetMaxTokensBtn.removeEventListener('click', this.resetMaxTokensHandler);
        }
        if (this.resetTemperatureBtn) {
            this.resetTemperatureBtn.removeEventListener('click', this.resetTemperatureHandler);
        }
        if (this.cancelBtn) {
            this.cancelBtn.removeEventListener('click', this.cancelHandler);
        }
        if (this.applyBtn) {
            this.applyBtn.removeEventListener('click', this.applyHandler);
        }
        if (this.modal) {
            this.modal.removeEventListener('click', this.overlayClickHandler);
        }

        // Создаём новые обработчики с привязкой к this
        this.maxTokensInputHandler = (e) => {
            this.maxTokensValue.textContent = e.target.value;
        };
        this.temperatureInputHandler = (e) => {
            this.temperatureValue.textContent = parseFloat(e.target.value).toFixed(2);
        };
        this.resetMaxTokensHandler = () => {
            if (this.maxTokensSlider) {
                this.maxTokensSlider.value = this.defaultMaxTokens;
                this.maxTokensValue.textContent = this.defaultMaxTokens;
            }
        };
        this.resetTemperatureHandler = () => {
            if (this.temperatureSlider) {
                this.temperatureSlider.value = this.defaultTemperature;
                this.temperatureValue.textContent = this.defaultTemperature.toFixed(2);
            }
        };
        this.cancelHandler = () => this.hide();
        this.applyHandler = () => this.applySettings();
        this.overlayClickHandler = (e) => {
            if (e.target === this.modal) {
                this.hide();
            }
        };

        // Назначаем новые обработчики
        if (this.maxTokensSlider) {
            this.maxTokensSlider.addEventListener('input', this.maxTokensInputHandler);
        }
        if (this.temperatureSlider) {
            this.temperatureSlider.addEventListener('input', this.temperatureInputHandler);
        }
        if (this.resetMaxTokensBtn) {
            this.resetMaxTokensBtn.addEventListener('click', this.resetMaxTokensHandler);
        }
        if (this.resetTemperatureBtn) {
            this.resetTemperatureBtn.addEventListener('click', this.resetTemperatureHandler);
        }
        if (this.cancelBtn) {
            this.cancelBtn.addEventListener('click', this.cancelHandler);
        }
        if (this.applyBtn) {
            this.applyBtn.addEventListener('click', this.applyHandler);
        }
        if (this.modal) {
            this.modal.addEventListener('click', this.overlayClickHandler);
        }

        // Глобальный обработчик Escape (один раз)
        if (!this.escapeHandler) {
            this.escapeHandler = (e) => {
                if (e.key === 'Escape' && this.modal?.style.display !== 'none') {
                    this.hide();
                }
            };
            document.addEventListener('keydown', this.escapeHandler);
        }
    }

    init() {
        this.createModal();
    }

    show(settingsData) {
        this.currentSettings = settingsData;

        // Сохраняем дефолтные значения из конфига в поля класса
        this.defaultMaxTokens = settingsData.default_max_tokens;
        this.defaultTemperature = settingsData.default_temperature;

        // Обновляем ссылки на DOM
        this.refreshElements();

        // Перепривязываем обработчики
        this.attachEvents();

        // Устанавливаем диапазоны
        this.maxTokensSlider.min = settingsData.min_max_tokens;
        this.maxTokensSlider.max = settingsData.max_max_tokens;
        this.maxTokensSlider.step = settingsData.step_max_tokens;

        this.temperatureSlider.min = settingsData.min_temperature;
        this.temperatureSlider.max = settingsData.max_temperature;
        this.temperatureSlider.step = settingsData.step_temperature;

        // Текущие значения
        this.maxTokensSlider.value = settingsData.current_max_tokens;
        this.maxTokensValue.textContent = settingsData.current_max_tokens;

        this.temperatureSlider.value = settingsData.current_temperature;
        this.temperatureValue.textContent = settingsData.current_temperature.toFixed(2);

        // Показываем окно
        this.modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    hide() {
        if (this.modal) {
            this.modal.style.display = 'none';
        }
        document.body.style.overflow = '';
        this.currentSettings = null;
    }

    applySettings() {
        const maxTokens = parseInt(this.maxTokensSlider.value, 10);
        const temperature = parseFloat(this.temperatureSlider.value);

        const settings = {
            max_tokens: maxTokens,
            temperature: temperature
        };

        if (window.sendCommand) {
            window.sendCommand('settings:apply:' + JSON.stringify(settings));
        } else {
            const chatInput = window.getChatInputField();
            if (chatInput) {
                chatInput.value = 'settings:apply:' + JSON.stringify(settings);
                chatInput.dispatchEvent(new Event('input', { bubbles: true }));
                setTimeout(() => { chatInput.value = ''; }, 50);
            }
        }

        this.hide();
    }

    isVisible() {
        return this.modal && this.modal.style.display !== 'none';
    }
}

// Создаём глобальный экземпляр
window.settingsModal = new SettingsModal();

window.showSettingsModal = function(settingsData) {
    if (!window.settingsModal) {
        return;
    }
    window.settingsModal.show(settingsData);
};