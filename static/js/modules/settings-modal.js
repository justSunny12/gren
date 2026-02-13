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

        // Ссылки на DOM-элементы
        this.maxTokensSlider = null;
        this.temperatureSlider = null;
        this.maxTokensValue = null;
        this.temperatureValue = null;
        this.resetMaxTokensBtn = null;
        this.resetTemperatureBtn = null;
        this.cancelBtn = null;
        this.applyBtn = null;

        // Обработчики (именованные, чтобы можно было удалить)
        this.maxTokensInputHandler = null;
        this.temperatureInputHandler = null;
        this.resetMaxTokensHandler = null;
        this.resetTemperatureHandler = null;
        this.cancelHandler = null;
        this.applyHandler = null;
        this.overlayClickHandler = null;
        this.escapeHandler = null;

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

    // Удаляет все ранее привязанные обработчики
    detachEvents() {
        if (this.maxTokensSlider && this.maxTokensInputHandler) {
            this.maxTokensSlider.removeEventListener('input', this.maxTokensInputHandler);
        }
        if (this.temperatureSlider && this.temperatureInputHandler) {
            this.temperatureSlider.removeEventListener('input', this.temperatureInputHandler);
        }
        if (this.resetMaxTokensBtn && this.resetMaxTokensHandler) {
            this.resetMaxTokensBtn.removeEventListener('click', this.resetMaxTokensHandler);
        }
        if (this.resetTemperatureBtn && this.resetTemperatureHandler) {
            this.resetTemperatureBtn.removeEventListener('click', this.resetTemperatureHandler);
        }
        if (this.cancelBtn && this.cancelHandler) {
            this.cancelBtn.removeEventListener('click', this.cancelHandler);
        }
        if (this.applyBtn && this.applyHandler) {
            this.applyBtn.removeEventListener('click', this.applyHandler);
        }
        if (this.modal && this.overlayClickHandler) {
            this.modal.removeEventListener('click', this.overlayClickHandler);
        }
        // EscapeHandler глобальный, удаляем только если он был добавлен
        if (this.escapeHandler) {
            document.removeEventListener('keydown', this.escapeHandler);
            this.escapeHandler = null;
        }
    }

    // Создаёт и привязывает новые обработчики
    attachEvents() {
        // Создаём обработчики с привязкой к this
        this.maxTokensInputHandler = (e) => {
            this.maxTokensValue.textContent = e.target.value;
        };
        this.temperatureInputHandler = (e) => {
            this.temperatureValue.textContent = parseFloat(e.target.value).toFixed(2);
        };
        this.resetMaxTokensHandler = () => {
            console.log('[SettingsModal] reset max tokens to default:', this.defaultMaxTokens);
            if (this.maxTokensSlider) {
                this.maxTokensSlider.value = this.defaultMaxTokens;
                this.maxTokensValue.textContent = this.defaultMaxTokens;
            }
        };
        this.resetTemperatureHandler = () => {
            console.log('[SettingsModal] reset temperature to default:', this.defaultTemperature);
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
        this.escapeHandler = (e) => {
            if (e.key === 'Escape' && this.modal?.style.display !== 'none') {
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
        // Глобальный обработчик Escape
        document.addEventListener('keydown', this.escapeHandler);
    }

    init() {
        this.createModal();
    }

    show(settingsData) {
        console.log('[SettingsModal] show with data:', settingsData);
        this.currentSettings = settingsData;

        // Сохраняем дефолтные значения из конфига
        this.defaultMaxTokens = settingsData.default_max_tokens;
        this.defaultTemperature = settingsData.default_temperature;

        // Обновляем ссылки на DOM
        this.refreshElements();

        // Удаляем старые обработчики и привязываем новые
        this.detachEvents();
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

        console.log('[SettingsModal] apply settings:', settings);

        // Отправляем команду на сервер
        if (window.sendCommand) {
            window.sendCommand('settings:apply:' + JSON.stringify(settings));
        }

        // Обновляем кэш настроек на клиенте
        if (window.appSettings) {
            window.appSettings.current_max_tokens = maxTokens;
            window.appSettings.current_temperature = temperature;
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
        console.error('settingsModal не инициализирован');
        return;
    }
    window.settingsModal.show(settingsData);
};