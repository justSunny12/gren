/* static/js/modules/generation-control.js - Управление кнопками отправки и остановки */

// Состояние генерации
let isGenerating = false;
let generationCheckInterval = null; // <-- Добавляем объявление переменной

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
        // Показываем кнопку остановки, скрываем отправку
        sendBtn.classList.add('hidden');
        stopBtn.classList.add('active');
        sendBtn.disabled = true;
        
        // Запускаем периодическую проверку на случай, если генерация зависнет
        if (generationCheckInterval) {
            clearInterval(generationCheckInterval);
        }
        
        generationCheckInterval = setInterval(() => {
            // Проверяем, не завершилась ли генерация сама (fallback механизм)
            const isStillGenerating = sendBtn.classList.contains('hidden');
            if (!isStillGenerating && generationCheckInterval) {
                clearInterval(generationCheckInterval);
                generationCheckInterval = null;
            }
        }, 1000);
    } else {
        // Показываем кнопку отправки, скрываем остановку
        sendBtn.classList.remove('hidden');
        stopBtn.classList.remove('active');
        sendBtn.disabled = false;
        updateSendButtonState(); // Обновляем состояние кнопки отправки
        
        // Очищаем интервал проверки
        if (generationCheckInterval) {
            clearInterval(generationCheckInterval);
            generationCheckInterval = null;
        }
    }
}

// Функция для настройки иконки отправки
function setupSendButtonIcon() {
    const sendBtn = document.querySelector('.generation-buttons-wrapper .send-btn');
    
    if (!sendBtn) {
        setTimeout(setupSendButtonIcon, 100);
        return;
    }
    
    // Если иконка уже есть - ничего не делаем
    if (sendBtn.querySelector('svg')) {
        return;
    }
        
    // Очищаем кнопку
    sendBtn.innerHTML = '';
    
    // Создаем SVG для кнопки отправки
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

// Функция для настройки иконки остановки
function setupStopButtonIcon(stopBtn = null) {
    if (!stopBtn) {
        stopBtn = document.querySelector('.generation-buttons-wrapper .stop-btn');
    }
    
    if (!stopBtn) {
        return;
    }
    
    // Если иконка уже есть - ничего не делаем
    if (stopBtn.querySelector('svg')) {
        return;
    }
        
    // Очищаем кнопку
    stopBtn.innerHTML = '';
    
    // Создаем SVG для кнопки остановки
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

// Функция для обновления состояния кнопки отправки на основе поля ввода
function updateSendButtonState() {
    const sendBtn = document.querySelector('.generation-buttons-wrapper .send-btn');
    const chatInput = document.querySelector('.chat-input-wrapper textarea');
    
    if (!sendBtn || !chatInput || isGenerating) return;
    
    const text = chatInput.value.trim();
    const isEmpty = text === '';
    
    sendBtn.disabled = isEmpty;
    sendBtn.style.cursor = isEmpty ? 'not-allowed' : 'pointer';
}

// Функция для отслеживания изменений в поле ввода
function setupInputTracking() {
    const chatInput = document.querySelector('.chat-input-wrapper textarea');
    
    if (!chatInput) {
        // Если поле ввода еще не загружено, пробуем позже
        setTimeout(setupInputTracking, 100);
        return;
    }
    
    // Слушаем события ввода
    ['input', 'change', 'keyup', 'keydown', 'focus', 'blur'].forEach(eventType => {
        chatInput.addEventListener(eventType, function() {
            if (!isGenerating) {
                setTimeout(updateSendButtonState, 10);
            }
        });
    });
    
    // Устанавливаем начальное состояние
    updateSendButtonState();
}

// Функция для отслеживания начала генерации
function setupGenerationStartTracking() {
    // Отслеживаем клики на кнопке отправки
    const submitBtn = document.querySelector('.generation-buttons-wrapper .send-btn');
    if (submitBtn) {
        submitBtn.addEventListener('click', function(e) {
            const chatInput = document.querySelector('.chat-input-wrapper textarea');
            if (chatInput && chatInput.value.trim() !== '') {
                toggleGenerationButtons(true);
            }
        });
    }
    
    // Отслеживаем отправку по Enter
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

// Инициализация кнопок
async function initGenerationButtons() {
    
    // Ждем пока найдутся обе кнопки
    const { sendBtn, stopBtn } = await findGenerationButtons();
    
    if (!sendBtn || !stopBtn) {
        return;
    }
    
    // Настраиваем иконки
    setupSendButtonIcon(sendBtn);
    setupStopButtonIcon(stopBtn);
    
    // Настраиваем отслеживание ввода
    setupInputTracking();
    
    // Настраиваем отслеживание начала генерации
    setupGenerationStartTracking(sendBtn);
    
    // Назначаем обработчик для кнопки остановки
    if (stopBtn) {
        stopBtn.addEventListener('click', function(e) {
                        
            if (!isGenerating) {
                return;
            }
            
            toggleGenerationButtons(false);
        }, { capture: true });
    }
    
    // Устанавливаем начальное состояние (показываем отправку, скрываем остановку)
    toggleGenerationButtons(false);
}

// Экспортируем функции для использования в других модулях
window.toggleGenerationButtons = toggleGenerationButtons;
window.initGenerationButtons = initGenerationButtons;
window.updateSendButtonState = updateSendButtonState;
window.isGenerating = false; // Делаем доступным глобально

// Автоматическая инициализация при загрузке
document.addEventListener('DOMContentLoaded', function() {    
    // Инициализируем сразу
    initGenerationButtons();
    
    // Также инициализируем с задержками, на случай если Gradio загрузил компоненты позже
    const intervals = [100, 300, 500, 1000, 2000, 5000];
    intervals.forEach(timeout => {
        setTimeout(() => {
            initGenerationButtons();
        }, timeout);
    });
});

// Также отслеживаем обновления Gradio
if (window.gradio_app) {
    document.addEventListener('gradio_update', function() {
        setTimeout(initGenerationButtons, 100);
    });
}

// MutationObserver для отслеживания изменений DOM
const observer = new MutationObserver(function(mutations) {
    for (const mutation of mutations) {
        if (mutation.type === 'childList') {
            // Проверяем, добавились ли новые кнопки
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

// Начинаем наблюдение
observer.observe(document.body, {
    childList: true,
    subtree: true
});