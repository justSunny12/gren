/* static/js/modules/send-button.js - Модуль для настройки круглой кнопки отправки */

// Функция для добавления SVG иконки в круглую кнопку
function setupSendButtonIcon() {
    const sendButtons = document.querySelectorAll('.send-btn-wrapper button');
    sendButtons.forEach(button => {
        // Очищаем кнопку от всего
        button.innerHTML = '';
        
        // Создаем ваш точный SVG
        const svgNS = 'http://www.w3.org/2000/svg';
        const svg = document.createElementNS(svgNS, 'svg');
        
        // Устанавливаем ВСЕ атрибуты как в вашем SVG
        svg.setAttribute('xmlns', svgNS);
        svg.setAttribute('width', '20');
        svg.setAttribute('height', '20');
        svg.setAttribute('viewBox', '0 0 24 24');
        svg.setAttribute('fill', 'none');
        svg.setAttribute('stroke', 'currentColor');
        svg.setAttribute('stroke-width', '2');
        svg.setAttribute('stroke-linecap', 'round');
        svg.setAttribute('stroke-linejoin', 'round');
        svg.setAttribute('class', 'lucide lucide-arrow-up-icon lucide-arrow-up');
        
        // Первый path
        const path1 = document.createElementNS(svgNS, 'path');
        path1.setAttribute('d', 'm5 12 7-7 7 7');
        
        // Второй path
        const path2 = document.createElementNS(svgNS, 'path');
        path2.setAttribute('d', 'M12 19V5');
        
        // Добавляем path в SVG
        svg.appendChild(path1);
        svg.appendChild(path2);
        
        // Добавляем SVG в кнопку
        button.appendChild(svg);
        
        // Стили для SVG чтобы он был белым и правильно позиционировался
        svg.style.width = '20px';
        svg.style.height = '20px';
        svg.style.display = 'block';
        svg.style.color = 'white';
        svg.style.stroke = 'currentColor';
    });
}

// Функция для обновления состояния кнопки на основе содержимого поля ввода
function updateSendButtonState() {
    const sendButtons = document.querySelectorAll('.send-btn-wrapper button');
    const chatInputs = document.querySelectorAll('.chat-input-wrapper textarea');
    
    if (chatInputs.length === 0 || sendButtons.length === 0) {
        return;
    }
    
    const chatInput = chatInputs[0];
    const sendButton = sendButtons[0];
    
    const text = chatInput.value.trim();
    const isEmpty = text === '';
    
    // Обновляем состояние кнопки
    sendButton.disabled = isEmpty;
    sendButton.style.cursor = isEmpty ? 'not-allowed' : 'pointer';
    
    // Убираем любой title, который мог остаться
    if (sendButton.hasAttribute('title')) {
        sendButton.removeAttribute('title');
    }
}

// Функция для отслеживания изменений в поле ввода
function setupInputTracking() {
    const chatInputs = document.querySelectorAll('.chat-input-wrapper textarea');
    
    if (chatInputs.length === 0) {
        // Если поле ввода еще не загружено, ждем и пробуем снова
        setTimeout(setupInputTracking, 100);
        return;
    }
    
    const chatInput = chatInputs[0];
    
    // Слушаем события ввода, изменения и фокуса
    ['input', 'change', 'keyup', 'keydown', 'focus', 'blur'].forEach(eventType => {
        chatInput.addEventListener(eventType, function() {
            setTimeout(updateSendButtonState, 10);
        });
    });
    
    // Устанавливаем начальное состояние
    updateSendButtonState();
    
    // Также отслеживаем изменения DOM через MutationObserver
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                setTimeout(updateSendButtonState, 10);
            }
        });
    });
    
    // Наблюдаем за изменениями в поле ввода и его родителях
    observer.observe(chatInput, {
        characterData: true,
        childList: true,
        subtree: true
    });
}

// Запускаем сразу и периодически проверяем
function initButtons() {
    setupSendButtonIcon();
    setupInputTracking();
    
    // Дополнительная проверка через интервалы
    const intervals = [100, 500, 1000, 2000];
    intervals.forEach(timeout => {
        setTimeout(() => {
            setupSendButtonIcon();
            setupInputTracking();
        }, timeout);
    });
}

// Запускаем при загрузке
document.addEventListener('DOMContentLoaded', initButtons);

// И при обновлении интерфейса Gradio
if (window.gradio_app) {
    document.addEventListener('gradio_update', initButtons);
}

// MutationObserver для отслеживания динамических изменений
const buttonObserver = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        if (mutation.type === 'childList') {
            // Проверяем, добавились ли новые кнопки
            const hasNewButtons = mutation.addedNodes && Array.from(mutation.addedNodes).some(node => {
                return node.classList && node.classList.contains('send-btn-wrapper') ||
                    node.querySelector && node.querySelector('.send-btn-wrapper');
            });
            
            // Проверяем, добавились ли новые поля ввода
            const hasNewInputs = mutation.addedNodes && Array.from(mutation.addedNodes).some(node => {
                return node.classList && node.classList.contains('chat-input-wrapper') ||
                    node.querySelector && node.querySelector('.chat-input-wrapper');
            });
            
            if (hasNewButtons || hasNewInputs) {
                setTimeout(() => {
                    setupSendButtonIcon();
                    setupInputTracking();
                }, 100);
            }
        }
    });
});

// Начинаем наблюдение
buttonObserver.observe(document.body, {
    childList: true,
    subtree: true
});

// Также запускаем при кликах и фокусе (на всякий случай)
document.addEventListener('click', function() {
    setTimeout(setupSendButtonIcon, 50);
    setTimeout(updateSendButtonState, 50);
});

document.addEventListener('focus', function() {
    setTimeout(setupSendButtonIcon, 50);
    setTimeout(updateSendButtonState, 50);
}, true);