/* static/js/modules/autoscroll.js */

(function () {
    var SELECTOR  = '.chat-window-container .block.chatbot';
    var container = null;
    var observer  = null;
    var pinned    = true;
    var lastScrollTop = 0;
    var isProgrammaticScroll = false;

    function scrollToBottom() {
        if (!container) return;
        isProgrammaticScroll = true;
        container.scrollTop = container.scrollHeight;
        lastScrollTop = container.scrollTop;
    }

    function onScroll() {
        if (!container) return;
        if (isProgrammaticScroll) {
            isProgrammaticScroll = false;
            lastScrollTop = container.scrollTop;
            return;
        }
        var current = container.scrollTop;
        if (current < lastScrollTop) {
            pinned = false;
        } else {
            var fromBottom = container.scrollHeight - current - container.clientHeight;
            if (fromBottom <= 0) pinned = true;
        }
        lastScrollTop = current;
    }

    function onMutation() {
        if (container && pinned) scrollToBottom();
    }

    function start() {
        container = document.querySelector(SELECTOR);
        if (!container) { setTimeout(start, 100); return; }
        pinned = true;
        scrollToBottom();
        container.addEventListener('scroll', onScroll, { passive: true });
        observer = new MutationObserver(onMutation);
        observer.observe(container, { childList: true, subtree: true, characterData: true });
    }

    function stop() {
        if (observer)  { observer.disconnect(); observer = null; }
        if (container) { container.removeEventListener('scroll', onScroll); }
        container = null;
        pinned    = true;
        lastScrollTop = 0;
        isProgrammaticScroll = false;
    }

    var _orig = window.toggleGenerationButtons;
    window.toggleGenerationButtons = function (generating) {
        generating ? start() : stop();
        if (_orig) _orig(generating);
    };
})();