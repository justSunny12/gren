/* static/js/modules/settings-modal.js - Модальное окно настроек генерации */

(function() {
    class SettingsModal {
        constructor() {
            this.modal = null;
            this.maxTokensSlider = null;
            this.temperatureSlider = null;
            this.maxTokensValue = null;
            this.temperatureValue = null;
            this.maxTokensReset = null;
            this.temperatureReset = null;
            this.confirmBtn = null;
            this.cancelBtn = null;
            this.isVisible = false;

            this.init();
        }

        init() {
            // Создаём DOM-структуру
            this.createModal();
            // Привязываем обработчики
            this.bindEvents();
        }

        createModal() {
            const modalHTML = `
                <div id="settingsModal" class="modal-overlay" style="display: none;">
                    <div class="modal-container gen-settings-modal-container">
                        <div class="modal-header">
                            <h3 class="modal-title">Настройки генерации</h3>
                        </div>
                        <div class="modal-content">
                            <div class="gen-settings-section">
                                <div class="gen-settings-label">
                                    <span>Максимум токенов</span>
                                    <button class="gen-settings-reset-btn" id="resetMaxTokensBtn">🔄</button>
                                </div>
                                <div class="gen-settings-slider-wrapper">
                                    <input type="range" id="settingsMaxTokens" class="gen-settings-slider" 
                                        min="64" max="4096" step="64">
                                    <span id="settingsMaxTokensValue" class="gen-settings-value">2048</span>
                                </div>
                            </div>
                            <div class="gen-settings-section">
                                <div class="gen-settings-label">
                                    <span>Температура</span>
                                    <button class="gen-settings-reset-btn" id="resetTemperatureBtn">🔄</button>
                                </div>
                                <div class="gen-settings-slider-wrapper">
                                    <input type="range" id="settingsTemperature" class="gen-settings-slider" 
                                        min="0.1" max="1.5" step="0.05">
                                    <span id="settingsTemperatureValue" class="gen-settings-value">0.70</span>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button id="settingsCancelBtn" class="modal-btn cancel">Отмена</button>
                            <button id="settingsApplyBtn" class="modal-btn confirm">Применить</button>
                        </div>
                    </div>
                </div>
            `;

            const container = document.createElement('div');
            container.innerHTML = modalHTML;
            document.body.appendChild(container);

            this.modal = document.getElementById('gen-settingsModal');
            this.maxTokensSlider = document.getElementById('gen-settingsMaxTokens');
            this.temperatureSlider = document.getElementById('gen-settingsTemperature');
            this.maxTokensValue = document.getElementById('gen-settingsMaxTokensValue');
            this.temperatureValue = document.getElementById('gen-settingsTemperatureValue');
            this.maxTokensReset = document.getElementById('resetMaxTokensBtn');
            this.temperatureReset = document.getElementById('resetTemperatureBtn');
            this.confirmBtn = document.getElementById('gen-settingsApplyBtn');
            this.cancelBtn = document.getElementById('gen-settingsCancelBtn');
        }

        bindEvents() {
            // Обновление отображаемых значений при движении слайдеров
            this.maxTokensSlider.addEventListener('input', () => {
                this.maxTokensValue.textContent = this.maxTokensSlider.value;
            });
            this.temperatureSlider.addEventListener('input', () => {
                this.temperatureValue.textContent = parseFloat(this.temperatureSlider.value).toFixed(2);
            });

            // Кнопки сброса
            this.maxTokensReset.addEventListener('click', () => {
                const defaultVal = window.lastChatListData?._default_max_tokens || 2048;
                this.maxTokensSlider.value = defaultVal;
                this.maxTokensValue.textContent = defaultVal;
            });
            this.temperatureReset.addEventListener('click', () => {
                const defaultVal = window.lastChatListData?._default_temperature || 0.7;
                this.temperatureSlider.value = defaultVal;
                this.temperatureValue.textContent = defaultVal.toFixed(2);
            });

            // Кнопка "Применить"
            this.confirmBtn.addEventListener('click', () => this.applySettings());

            // Кнопка "Отмена"
            this.cancelBtn.addEventListener('click', () => this.hide());

            // Закрытие по клику на оверлей
            this.modal.addEventListener('click', (e) => {
                if (e.target === this.modal) {
                    this.hide();
                }
            });

            // Закрытие по ESC
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.isVisible) {
                    this.hide();
                }
            });
        }

        show() {
            if (window.closeAllContextMenus) {
            window.closeAllContextMenus();
    }
            // Загружаем актуальные данные из window.lastChatListData
            const data = window.lastChatListData || {};
            
            // Устанавливаем атрибуты слайдеров из данных
            this.maxTokensSlider.min = data._min_max_tokens || 64;
            this.maxTokensSlider.max = data._max_max_tokens || 4096;
            this.maxTokensSlider.step = data._step_max_tokens || 64;
            this.temperatureSlider.min = data._min_temperature || 0.1;
            this.temperatureSlider.max = data._max_temperature || 1.5;
            this.temperatureSlider.step = data._step_temperature || 0.05;

            // Текущие значения
            const currentMax = data._current_max_tokens !== undefined ? data._current_max_tokens : 2048;
            const currentTemp = data._current_temperature !== undefined ? data._current_temperature : 0.7;

            this.maxTokensSlider.value = currentMax;
            this.maxTokensValue.textContent = currentMax;
            this.temperatureSlider.value = currentTemp;
            this.temperatureValue.textContent = currentTemp.toFixed(2);

            this.modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
            this.isVisible = true;
        }

        hide() {
            this.modal.style.display = 'none';
            document.body.style.overflow = '';
            this.isVisible = false;
        }

        applySettings() {
            const maxTokens = parseInt(this.maxTokensSlider.value, 10);
            const temperature = parseFloat(this.temperatureSlider.value);

            const settings = {
                max_tokens: maxTokens,
                temperature: temperature
            };

            // Отправляем команду через скрытое поле
            const chatInput = window.getChatInputField();
            if (chatInput) {
                const command = `settings:apply:${JSON.stringify(settings)}`;
                chatInput.value = command;
                chatInput.dispatchEvent(new Event('input', { bubbles: true }));
                // Очищаем поле через короткое время, чтобы не мешать
                setTimeout(() => { chatInput.value = ''; }, 100);
            }

            this.hide();
        }

        isVisible() {
            return this.isVisible;
        }
    }

    // Глобальный экземпляр
    window.settingsModal = new SettingsModal();

    // Инициализация обработчика кнопки
    window.initSettingsButton = function() {
        const settingsBtn = document.querySelector('.settings-btn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                if (window.settingsModal) {
                    window.settingsModal.show();
                }
            });
        } else {
            // Если кнопка ещё не загружена, пробуем позже
            setTimeout(window.initSettingsButton, 200);
        }
    };

    // Автозапуск
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', window.initSettingsButton);
    } else {
        window.initSettingsButton();
    }

    // Также запускаем через MutationObserver на случай динамической загрузки
    const observer = new MutationObserver(() => {
        if (!document.querySelector('.settings-btn')) return;
        window.initSettingsButton();
        observer.disconnect();
    });
    observer.observe(document.body, { childList: true, subtree: true });
})();