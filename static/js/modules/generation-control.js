/* static/js/modules/generation-control.js - Управление кнопками отправки и остановки */
/* Добавлены функции setupThinkingButtonIcon, setupSearchButtonIcon, setupAttachButtonIcon */

// Состояние генерации
let isGenerating = false;
let generationCheckInterval = null;

function findGenerationButtons(maxAttempts = 10, interval = 100) {
    return new Promise((resolve, reject) => {
        let attempts = 0;
        
        const searchButtons = () => {
            attempts++;
            
            const sendBtn = document.querySelector('.generation-buttons-wrapper .send-btn');
            const stopBtn = document.querySelector('.generation-buttons-wrapper .stop-btn');
            
            if (sendBtn && stopBtn) {
                resolve({ sendBtn, stopBtn });
                return;
            }
            
            if (attempts >= maxAttempts) {
                resolve({ sendBtn: null, stopBtn: null });
                return;
            }
            
            setTimeout(searchButtons, interval);
        };
        
        searchButtons();
    });
}

// Функция для переключения видимости кнопок
function toggleGenerationButtons(generating) {
    const sendBtn = document.querySelector('.generation-buttons-wrapper .send-btn');
    const stopBtn = document.querySelector('.generation-buttons-wrapper .stop-btn');
    
    if (!sendBtn || !stopBtn) {
        return;
    }
    
    isGenerating = generating;
    
    if (generating) {
        sendBtn.classList.add('hidden');
        stopBtn.classList.add('active');
        sendBtn.disabled = true;
        
        if (generationCheckInterval) {
            clearInterval(generationCheckInterval);
        }
        
        generationCheckInterval = setInterval(() => {
            const isStillGenerating = sendBtn.classList.contains('hidden');
            if (!isStillGenerating && generationCheckInterval) {
                clearInterval(generationCheckInterval);
                generationCheckInterval = null;
            }
        }, 1000);
    } else {
        sendBtn.classList.remove('hidden');
        stopBtn.classList.remove('active');
        sendBtn.disabled = false;
        updateSendButtonState();
        
        if (generationCheckInterval) {
            clearInterval(generationCheckInterval);
            generationCheckInterval = null;
        }
    }
}

// --- Существующие функции для send и stop (без изменений) ---
function setupSendButtonIcon() {
    const sendBtn = document.querySelector('.generation-buttons-wrapper .send-btn');
    if (!sendBtn) {
        setTimeout(setupSendButtonIcon, 100);
        return;
    }
    if (sendBtn.querySelector('svg')) {
        return;
    }
    sendBtn.innerHTML = '';
    
    const sendSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    sendSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    sendSvg.setAttribute('width', '20');
    sendSvg.setAttribute('height', '20');
    sendSvg.setAttribute('viewBox', '0 0 24 24');
    sendSvg.setAttribute('fill', 'none');
    sendSvg.setAttribute('stroke', 'currentColor');
    sendSvg.setAttribute('stroke-width', '2.5');
    sendSvg.setAttribute('stroke-linecap', 'round');
    sendSvg.setAttribute('stroke-linejoin', 'round');
    sendSvg.setAttribute('class', 'lucide lucide-arrow-up-icon lucide-arrow-up');
    
    const path1 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path1.setAttribute('d', 'm5 12 7-7 7 7');
    const path2 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path2.setAttribute('d', 'M12 19V5');
    
    sendSvg.appendChild(path1);
    sendSvg.appendChild(path2);
    sendBtn.appendChild(sendSvg);
}

function setupStopButtonIcon(stopBtn = null) {
    if (!stopBtn) {
        stopBtn = document.querySelector('.generation-buttons-wrapper .stop-btn');
    }
    if (!stopBtn) return;
    if (stopBtn.querySelector('svg')) return;
    
    stopBtn.innerHTML = '';
    
    const stopSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    stopSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    stopSvg.setAttribute('width', '20');
    stopSvg.setAttribute('height', '20');
    stopSvg.setAttribute('viewBox', '0 0 24 24');
    stopSvg.setAttribute('fill', 'none');
    stopSvg.setAttribute('stroke', 'currentColor');
    stopSvg.setAttribute('stroke-width', '2');
    stopSvg.setAttribute('stroke-linecap', 'round');
    stopSvg.setAttribute('stroke-linejoin', 'round');
    stopSvg.setAttribute('class', 'lucide lucide-octagon-x-icon lucide-octagon-x');
    
    const path1 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path1.setAttribute('d', 'm15 9-6 6');
    const path2 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path2.setAttribute('d', 'M2.586 16.726A2 2 0 0 1 2 15.312V8.688a2 2 0 0 1 .586-1.414l4.688-4.688A2 2 0 0 1 8.688 2h6.624a2 2 0 0 1 1.414.586l4.688 4.688A2 2 0 0 1 22 8.688v6.624a2 2 0 0 1-.586 1.414l-4.688 4.688a2 2 0 0 1-1.414.586H8.688a2 2 0 0 1-1.414-.586z');
    const path3 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path3.setAttribute('d', 'm9 9 6 6');
    
    stopSvg.appendChild(path1);
    stopSvg.appendChild(path2);
    stopSvg.appendChild(path3);
    stopBtn.appendChild(stopSvg);
}

// ========== НОВЫЕ ФУНКЦИИ ДЛЯ ДОПОЛНИТЕЛЬНЫХ КНОПОК ==========

/**
 * Устанавливает иконку для кнопки "Глубокое мышление" (thinking-btn)
 * Иконка атома (lucide atom) помещается слева от текста.
 */
function setupThinkingButtonIcon() {
    const thinkingBtn = document.querySelector('.generation-buttons-wrapper .thinking-btn');
    if (!thinkingBtn) return;
    // Если иконка уже добавлена — не дублируем
    if (thinkingBtn.querySelector('svg')) return;

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    svg.setAttribute('width', '18');
    svg.setAttribute('height', '18');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '2');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');
    svg.setAttribute('class', 'lucide lucide-atom-icon lucide-atom');

    // Содержимое SVG: <circle cx="12" cy="12" r="1"/> и два <path>
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', '12');
    circle.setAttribute('cy', '12');
    circle.setAttribute('r', '1');

    const path1 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path1.setAttribute('d', 'M20.2 20.2c2.04-2.03.02-7.36-4.5-11.9-4.54-4.52-9.87-6.54-11.9-4.5-2.04 2.03-.02 7.36 4.5 11.9 4.54 4.52 9.87 6.54 11.9 4.5Z');

    const path2 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path2.setAttribute('d', 'M15.7 15.7c4.52-4.54 6.54-9.87 4.5-11.9-2.03-2.04-7.36-.02-11.9 4.5-4.52 4.54-6.54 9.87-4.5 11.9 2.03 2.04 7.36.02 11.9-4.5Z');

    svg.appendChild(circle);
    svg.appendChild(path1);
    svg.appendChild(path2);

    // Вставляем SVG в начало кнопки — текст останется справа
    thinkingBtn.insertBefore(svg, thinkingBtn.firstChild);
}

/**
 * Устанавливает иконку для кнопки "Поиск" (search-btn)
 * Иконка глобуса (lucide globe) помещается слева от текста.
 */
function setupSearchButtonIcon() {
    const searchBtn = document.querySelector('.generation-buttons-wrapper .search-btn');
    if (!searchBtn) return;
    if (searchBtn.querySelector('svg')) return;

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    svg.setAttribute('width', '18');
    svg.setAttribute('height', '18');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '2');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');
    svg.setAttribute('class', 'lucide lucide-globe-icon lucide-globe');

    // Содержимое: <circle cx="12" cy="12" r="10"/> и два <path>
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', '12');
    circle.setAttribute('cy', '12');
    circle.setAttribute('r', '10');

    const path1 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path1.setAttribute('d', 'M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20');

    const path2 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path2.setAttribute('d', 'M2 12h20');

    svg.appendChild(circle);
    svg.appendChild(path1);
    svg.appendChild(path2);

    searchBtn.insertBefore(svg, searchBtn.firstChild);
}

/**
 * Устанавливает иконку для кнопки "Прикрепить файл" (attach-btn)
 */
function setupAttachButtonIcon() {
    const btn = document.querySelector('.generation-buttons-wrapper .attach-btn');
    if (!btn) return;
    if (btn.querySelector('svg.deepseek-attach-icon')) return; // проверка по классу

    btn.innerHTML = '';

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    svg.setAttribute('version', '1.0');
    svg.setAttribute('viewBox', '0 0 316 332');  // оригинальный viewBox
    svg.setAttribute('width', '50');
    svg.setAttribute('height', '50');
    svg.setAttribute('fill', 'currentColor');
    svg.setAttribute('stroke', 'none');  // важно: это fill-иконка, а не stroke
    svg.classList.add('deepseek-attach-icon');  // уникальный класс для CSS
    svg.style.setProperty('left', 'calc(50% + 1px)', 'important');

    // Ваш точный SVG-клон
    svg.innerHTML = `
        <path d="M136.7 114c-9.2 2.3-16 8-19.9 16.5-2.1 4.6-2.3 6.7-2.6 25.7-.2 11.4.1 23.7.7 27.3 3.3 21.7 21.4 36.7 42.5 35.2 13.1-.9 24.1-6.9 31-17 6.6-9.6 6.9-11.6 7.4-38.5l.4-24.2h-9l-.4 22.7c-.5 25.9-1.2 29.1-8 36.8-5.1 5.8-10.8 9.1-18.1 10.4-14.7 2.7-29.5-5.7-34.7-19.6-1.8-4.8-2-7.8-2-28.5 0-21.6.1-23.5 2.1-27.6 6.6-13.4 27.1-13.6 33.9-.1 1.8 3.5 2 5.9 2 26.2 0 21.1-.1 22.5-2 24.2-2.7 2.5-8 2.2-10.2-.6-1.6-1.8-1.8-4.4-1.8-19.5V146h-10v16.2c0 17.9.8 22.2 4.7 26.9 7.5 8.9 21.5 7.2 27.1-3.2 2.3-4.3 2.3-4.8 2-27.9-.3-22.4-.4-23.7-2.6-28-6.4-12.3-20.2-19-32.5-16"/>
    `;

    btn.appendChild(svg);
}

// --- Функция обновления состояния кнопки отправки ---
function updateSendButtonState() {
    const sendBtn = document.querySelector('.generation-buttons-wrapper .send-btn');
    const chatInput = document.querySelector('.chat-input-wrapper textarea');
    
    if (!sendBtn || !chatInput || isGenerating) return;
    
    const text = chatInput.value.trim();
    const isEmpty = text === '';
    
    sendBtn.disabled = isEmpty;
    sendBtn.style.cursor = isEmpty ? 'not-allowed' : 'pointer';
}

// --- Отслеживание изменений в поле ввода ---
function setupInputTracking() {
    const chatInput = document.querySelector('.chat-input-wrapper textarea');
    if (!chatInput) {
        setTimeout(setupInputTracking, 100);
        return;
    }
    
    ['input', 'change', 'keyup', 'keydown', 'focus', 'blur'].forEach(eventType => {
        chatInput.addEventListener(eventType, function() {
            if (!isGenerating) {
                setTimeout(updateSendButtonState, 10);
            }
        });
    });
    
    updateSendButtonState();
}

// --- Отслеживание начала генерации ---
function setupGenerationStartTracking() {
    const submitBtn = document.querySelector('.generation-buttons-wrapper .send-btn');
    if (submitBtn) {
        submitBtn.addEventListener('click', function(e) {
            const chatInput = document.querySelector('.chat-input-wrapper textarea');
            if (chatInput && chatInput.value.trim() !== '') {
                toggleGenerationButtons(true);
            }
        });
    }
    
    const chatInput = document.querySelector('.chat-input-wrapper textarea');
    if (chatInput) {
        chatInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey && !isGenerating) {
                if (chatInput.value.trim() !== '') {
                    setTimeout(() => {
                        toggleGenerationButtons(true);
                    }, 10);
                }
            }
        });
    }
}

function setupSettingsButtonIcon() {
    const btn = document.querySelector('.generation-buttons-wrapper .settings-btn');
    if (!btn) return;
    if (btn.querySelector('svg.lucide-settings')) return;

    btn.innerHTML = '';

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    svg.setAttribute('width', '20');
    svg.setAttribute('height', '20');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '2');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');
    svg.classList.add('lucide', 'lucide-settings');

    svg.innerHTML = `
        <path d="M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915"/>
        <circle cx="12" cy="12" r="3"/>
    `;

    btn.appendChild(svg);
}

// Обновляем существующую функцию initGenerationButtons
async function initGenerationButtons() {
    const { sendBtn, stopBtn } = await findGenerationButtons();
    if (sendBtn) setupSendButtonIcon(sendBtn);
    if (stopBtn) setupStopButtonIcon(stopBtn);

    // Добавляем вызовы новых функций
    setupThinkingButtonIcon();
    setupSearchButtonIcon();
    setupAttachButtonIcon();
    setupSettingsButtonIcon();

    // Остальной код без изменений
    setupInputTracking();
    setupGenerationStartTracking();

    if (stopBtn) {
        stopBtn.addEventListener('click', function(e) {
            if (!isGenerating) return;
            toggleGenerationButtons(false);
        }, { capture: true });
    }

    toggleGenerationButtons(false);
}

// Экспорт в глобальную область
window.toggleGenerationButtons = toggleGenerationButtons;
window.initGenerationButtons = initGenerationButtons;
window.updateSendButtonState = updateSendButtonState;
window.isGenerating = false;

// Автоматическая инициализация
document.addEventListener('DOMContentLoaded', function() {    
    initGenerationButtons();
    
    const intervals = [100, 300, 500, 1000, 2000, 5000];
    intervals.forEach(timeout => {
        setTimeout(() => {
            initGenerationButtons();
        }, timeout);
    });
});

if (window.gradio_app) {
    document.addEventListener('gradio_update', function() {
        setTimeout(initGenerationButtons, 100);
    });
}

// MutationObserver для отслеживания динамических изменений
const observer = new MutationObserver(function(mutations) {
    for (const mutation of mutations) {
        if (mutation.type === 'childList') {
            const hasNewButtons = Array.from(mutation.addedNodes).some(node => {
                return node.classList && node.classList.contains('generation-buttons-wrapper') ||
                       (node.querySelector && node.querySelector('.generation-buttons-wrapper'));
            });
            
            if (hasNewButtons) {
                setTimeout(initGenerationButtons, 100);
            }
        }
    }
});

observer.observe(document.body, {
    childList: true,
    subtree: true
});