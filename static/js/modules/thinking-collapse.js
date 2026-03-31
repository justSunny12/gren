/* static/js/modules/thinking-collapse.js
 *
 * Управление сворачиванием/разворачиванием блоков размышлений.
 * Добавлен фикс viewBox для иконок.
 *
 * Архитектура:
 *   • Python рендерит класс "thinking-done" для завершённых блоков.
 *     CSS скрывает тело блока через .thinking-done:not(.thinking-expanded).
 *   • JS управляет только классом "thinking-expanded":
 *     добавляет/убирает его при клике пользователя на заголовок.
 *   • MutationObserver восстанавливает "thinking-expanded" после каждого
 *     DOM-апдейта от Gradio (стриминг заменяет innerHTML сообщения).
 *   • userExpanded — Set индексов блоков, развёрнутых пользователем.
 *     Индекс = позиция .thinking-done среди всех .thinking-done в чатботе.
 *   • При смене диалога Set очищается.
 *   • Фикс viewBox: добавляем атрибут viewBox="0 0 24 24" для всех иконок,
 *     чтобы они масштабировались корректно и не обрезались.
 */

(function () {
    'use strict';

    var userExpanded = new Set();

    /* ── Helpers ── */

    function getChatbot() {
        return document.querySelector('.chat-window-container .chatbot');
    }

    function getDoneBlocks() {
        return document.querySelectorAll('.thinking-block.thinking-done');
    }

    function blockIndex(block) {
        return Array.prototype.indexOf.call(getDoneBlocks(), block);
    }

    /* ── Фикс viewBox для иконок ── */
    function fixChevronViewBox() {
        var chevrons = document.querySelectorAll('.thinking-chevron svg');
        for (var i = 0; i < chevrons.length; i++) {
            var svg = chevrons[i];
            if (!svg.getAttribute('viewBox')) {
                svg.setAttribute('viewBox', '0 0 24 24');
            }
        }
    }

    /* ── Восстановление thinking-expanded после замены DOM ── */

    function restoreExpanded() {
        if (userExpanded.size === 0) return;
        var blocks = getDoneBlocks();
        for (var i = 0; i < blocks.length; i++) {
            if (userExpanded.has(i)) {
                blocks[i].classList.add('thinking-expanded');
            }
        }
    }

    /* ── Обработчик клика (делегирование на чатбот) ── */

    function onChatbotClick(e) {
        // Кликабелен весь заголовок: p.thinking-header, p.thinking-header-stopped и т.д.
        var header = e.target.closest(
            '.thinking-header, .thinking-header-processing, .thinking-header-stopped'
        );
        if (!header) return;

        // Клик работает только для завершённых блоков
        var block = header.closest('.thinking-block.thinking-done');
        if (!block) return;

        var idx = blockIndex(block);

        if (block.classList.contains('thinking-expanded')) {
            block.classList.remove('thinking-expanded');
            userExpanded.delete(idx);
        } else {
            block.classList.add('thinking-expanded');
            userExpanded.add(idx);
        }
    }

    /* ── MutationObserver ── */

    var observer = null;

    function startObserver(chatbot) {
        if (observer) observer.disconnect();
        observer = new MutationObserver(function () {
            restoreExpanded();
            fixChevronViewBox();   // добавляем фикс иконок
        });
        observer.observe(chatbot, { childList: true, subtree: true });
    }

    /* ── Инициализация ── */

    function init() {
        var chatbot = getChatbot();
        if (!chatbot) {
            setTimeout(init, 100);
            return;
        }
        chatbot.addEventListener('click', onChatbotClick);
        startObserver(chatbot);
        fixChevronViewBox();   // чиним иконки при старте
    }

    /* ── Сброс при смене диалога ── */

    function clearState() {
        userExpanded.clear();
    }

    // Хук: переключение чата через selectChat (main.js, грузится после нас)
    // Оборачиваем с задержкой, чтобы поймать финальную версию функции
    setTimeout(function () {
        var orig = window.selectChat;
        window.selectChat = function (chatId) {
            clearState();
            if (orig) orig.apply(this, arguments);
        };
    }, 0);

    // Хук: renderChatList определён в chat-list.js, который грузится до нас
    var origRenderChatList = window.renderChatList;
    window.renderChatList = function (chats, scrollTarget) {
        var prev = window._thinkCollapseActiveId;
        var next = null;
        if (chats && typeof chats === 'object' && Array.isArray(chats.flat)) {
            var active = chats.flat.find(function (c) { return c.is_current; });
            if (active) next = active.id;
        }
        if (next !== null && next !== prev) {
            clearState();
            window._thinkCollapseActiveId = next;
            // после смены диалога DOM может перестроиться, чиним иконки с задержкой
            setTimeout(fixChevronViewBox, 50);
        }
        if (origRenderChatList) origRenderChatList.apply(this, arguments);
    };

    init();

})();