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
 * Иконка скрепки (lucide paperclip) повёрнута на -45 градусов.
 * Кнопка не содержит текста, поэтому полностью заменяем содержимое.
 */
function setupAttachButtonIcon() {
    const attachBtn = document.querySelector('.generation-buttons-wrapper .attach-btn');
    if (!attachBtn) return;
    if (attachBtn.querySelector('svg')) return;

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
    svg.setAttribute('class', 'lucide lucide-paperclip-icon lucide-paperclip');

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', 'm16 6-8.414 8.586a2 2 0 0 0 2.829 2.829l8.414-8.586a4 4 0 1 0-5.657-5.657l-8.379 8.551a6 6 0 1 0 8.485 8.485l8.379-8.551');

    svg.appendChild(path);

    // Полностью очищаем кнопку и вставляем SVG
    attachBtn.innerHTML = '';
    attachBtn.appendChild(svg);
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