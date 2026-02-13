/* static/js/modules/generation-control.js - Управление кнопками отправки, остановки и глубокого мышления */

// Глобальный флаг генерации (доступен из других модулей)
window.isGenerating = false;

let isGenerating = false;
let generationCheckInterval = null;
let currentThinkingButtonHandler = null;

function findGenerationButtons(maxAttempts = 10, interval = 100) {
    return new Promise((resolve) => {
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

window.toggleGenerationButtons = function(generating) {
    const sendBtn = document.querySelector('.generation-buttons-wrapper .send-btn');
    const stopBtn = document.querySelector('.generation-buttons-wrapper .stop-btn');
    if (!sendBtn || !stopBtn) return;
    
    isGenerating = generating;
    window.isGenerating = generating;   // синхронизируем глобальную переменную
    
    if (generating) {
        sendBtn.classList.add('hidden');
        stopBtn.classList.add('active');
        sendBtn.disabled = true;
        if (generationCheckInterval) clearInterval(generationCheckInterval);
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
        window.updateSendButtonState();
        if (generationCheckInterval) {
            clearInterval(generationCheckInterval);
            generationCheckInterval = null;
        }
    }
};

function setupSendButtonIcon() {
    const sendBtn = document.querySelector('.generation-buttons-wrapper .send-btn');
    if (!sendBtn) {
        setTimeout(setupSendButtonIcon, 100);
        return;
    }
    if (sendBtn.querySelector('svg')) return;
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

function setupStopButtonIcon() {
    const stopBtn = document.querySelector('.generation-buttons-wrapper .stop-btn');
    if (!stopBtn) return;
    if (stopBtn.querySelector('svg')) return;
    stopBtn.innerHTML = '';
    const stopSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    stopSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    stopSvg.setAttribute('width', '20');
    stopSvg.setAttribute('height', '20');
    stopSvg.setAttribute('viewBox', '0 0 24 24');
    stopSvg.setAttribute('fill', 'currentColor');
    stopSvg.setAttribute('stroke', 'none');
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', 'M2 12C2 7.28595 2 4.92893 3.46447 3.46447C4.92893 2 7.28595 2 12 2C16.714 2 19.0711 2 20.5355 3.46447C22 4.92893 22 7.28595 22 12C22 16.714 22 19.0711 20.5355 20.5355C19.0711 22 16.714 22 12 22C7.28595 22 4.92893 22 3.46447 20.5355C2 19.0711 2 16.714 2 12Z');
    stopSvg.appendChild(path);
    stopBtn.appendChild(stopSvg);
}

function setupThinkingButtonIcon() {
    const thinkingBtn = document.querySelector('.generation-buttons-wrapper .thinking-btn');
    if (!thinkingBtn) return;
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
    thinkingBtn.insertBefore(svg, thinkingBtn.firstChild);
}

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

function setupAttachButtonIcon() {
    const btn = document.querySelector('.generation-buttons-wrapper .attach-btn');
    if (!btn) return;
    if (btn.querySelector('svg')) return;
    btn.innerHTML = '';
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    svg.setAttribute('width', '20');
    svg.setAttribute('height', '20');
    svg.setAttribute('viewBox', '-4.5 0 24 24');
    svg.setAttribute('fill', 'currentColor');
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', 'm9.818 0c-3.012 0-5.455 2.442-5.455 5.455v9.818c0 1.808 1.465 3.273 3.273 3.273s3.273-1.465 3.273-3.273v-5.665c-.017-.589-.499-1.061-1.091-1.061s-1.074.471-1.091 1.059v.002 5.665.031c0 .603-.489 1.091-1.091 1.091s-1.091-.489-1.091-1.091c0-.011 0-.021 0-.032v.002-9.818c0-1.808 1.465-3.273 3.273-3.273s3.273 1.465 3.273 3.273v10.906c0 3.012-2.442 5.455-5.455 5.455s-5.455-2.442-5.455-5.455v-10.906c0-.009 0-.02 0-.031 0-.603-.489-1.091-1.091-1.091s-1.091.489-1.091 1.091v.032-.002 10.906c0 4.217 3.419 7.636 7.636 7.636s7.636-3.419 7.636-7.636v-10.906c-.003-3.011-2.444-5.452-5.455-5.455z');
    svg.appendChild(path);
    btn.appendChild(svg);
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

window.setThinkingButtonState = function(active) {
    const btn = document.querySelector('.generation-buttons-wrapper .thinking-btn');
    if (!btn) return;
    if (active) {
        btn.classList.add('thinking-btn-active');
        btn.setAttribute('data-active', 'true');
    } else {
        btn.classList.remove('thinking-btn-active');
        btn.setAttribute('data-active', 'false');
    }
};

function setupThinkingButtonHandler() {
    const thinkingBtn = document.querySelector('.generation-buttons-wrapper .thinking-btn');
    if (!thinkingBtn) {
        setTimeout(setupThinkingButtonHandler, 100);
        return;
    }
    if (currentThinkingButtonHandler) {
        thinkingBtn.removeEventListener('click', currentThinkingButtonHandler);
    }
    currentThinkingButtonHandler = function(e) {
        e.preventDefault();
        e.stopPropagation();
        const isActive = this.classList.contains('thinking-btn-active');
        window.setThinkingButtonState(!isActive);
        const chatInput = window.getChatInputField();
        if (chatInput) {
            const timestamp = Date.now();
            chatInput.value = 'thinking:toggle:' + timestamp;
            chatInput.dispatchEvent(new Event('input', { bubbles: true }));
            setTimeout(() => {
                chatInput.value = '';
            }, 100);
        }
    };
    thinkingBtn.addEventListener('click', currentThinkingButtonHandler);
}

window.updateSendButtonState = function() {
    const sendBtn = document.querySelector('.generation-buttons-wrapper .send-btn');
    const chatInput = document.querySelector('.chat-input-wrapper textarea');
    if (!sendBtn || !chatInput || isGenerating) return;
    const text = chatInput.value.trim();
    sendBtn.disabled = text === '';
    sendBtn.style.cursor = text === '' ? 'not-allowed' : 'pointer';
};

function setupInputTracking() {
    const chatInput = document.querySelector('.chat-input-wrapper textarea');
    if (!chatInput) {
        setTimeout(setupInputTracking, 100);
        return;
    }
    ['input', 'change', 'keyup', 'keydown', 'focus', 'blur'].forEach(eventType => {
        chatInput.addEventListener(eventType, function() {
            if (!isGenerating) {
                setTimeout(window.updateSendButtonState, 10);
            }
        });
    });
    window.updateSendButtonState();
}

function setupGenerationStartTracking() {
    const submitBtn = document.querySelector('.generation-buttons-wrapper .send-btn');
    if (submitBtn) {
        submitBtn.addEventListener('click', function() {
            const chatInput = document.querySelector('.chat-input-wrapper textarea');
            if (chatInput && chatInput.value.trim() !== '') {
                window.toggleGenerationButtons(true);
            }
        });
    }
    const chatInput = document.querySelector('.chat-input-wrapper textarea');
    if (chatInput) {
        chatInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey && !isGenerating) {
                if (chatInput.value.trim() !== '') {
                    setTimeout(() => {
                        window.toggleGenerationButtons(true);
                    }, 10);
                }
            }
        });
    }
}

window.initGenerationButtons = async function() {
    const { sendBtn, stopBtn } = await findGenerationButtons();
    if (sendBtn) setupSendButtonIcon(sendBtn);
    if (stopBtn) setupStopButtonIcon(stopBtn);
    setupThinkingButtonIcon();
    setupSearchButtonIcon();
    setupAttachButtonIcon();
    setupSettingsButtonIcon();
    setupInputTracking();
    setupGenerationStartTracking();
    setupThinkingButtonHandler();
    if (stopBtn) {
        stopBtn.addEventListener('click', function() {
            if (!isGenerating) return;
            window.toggleGenerationButtons(false);
        }, { capture: true });
    }
    window.toggleGenerationButtons(false);
};

document.addEventListener('DOMContentLoaded', function() {
    window.initGenerationButtons();
    [100, 300, 500, 1000, 2000, 5000].forEach(timeout => {
        setTimeout(() => window.initGenerationButtons(), timeout);
    });
});

if (window.gradio_app) {
    document.addEventListener('gradio_update', function() {
        setTimeout(window.initGenerationButtons, 100);
    });
}

const observer = new MutationObserver(function(mutations) {
    for (const mutation of mutations) {
        if (mutation.type === 'childList') {
            const hasNewButtons = Array.from(mutation.addedNodes).some(node => {
                return (node.classList && node.classList.contains('generation-buttons-wrapper')) ||
                       (node.querySelector && node.querySelector('.generation-buttons-wrapper'));
            });
            if (hasNewButtons) {
                setTimeout(window.initGenerationButtons, 100);
            }
        }
    }
});
observer.observe(document.body, { childList: true, subtree: true });

if (!window.getChatInputField) {
    window.getChatInputField = function() {
        const field = document.querySelector('#chat_input_field');
        return field ? field.querySelector('textarea') : null;
    };
}