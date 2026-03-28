var _scrollbarScrollEl = null;
var _scrollbarHoveredItem = null;
var _scrollbarFadeTimer = null;
var _scrollbarPointerTimer = null;
var _globalMouseX = 0;
var _globalMouseY = 0;
var _updateHoverRafId = null;
var _hoverDebounceTimer = null; // Переменная для дебаунса ховера

// Обновляем координаты при любом движении мыши (глобально)
document.addEventListener('mousemove', function(e) {
    _globalMouseX = e.clientX;
    _globalMouseY = e.clientY;
    // Если сейчас идёт скролл, обновляем кастомный ховер (но не при каждом движении, а через RAF)
    if (_scrollbarScrollEl && _scrollbarScrollEl.classList.contains('is-scrolling')) {
        // Добавляем дебаунс, чтобы обновление ховера происходило не каждый раз
        clearTimeout(_hoverDebounceTimer);
        _hoverDebounceTimer = setTimeout(function() {
            _scheduleHoverUpdate(); // Планируем обновление ховера
        }, 100); // 100 мс задержка
    }
}, { passive: true });

function _scheduleHoverUpdate() {
    if (_updateHoverRafId) cancelAnimationFrame(_updateHoverRafId);
    _updateHoverRafId = requestAnimationFrame(function() {
        _updateHoverRafId = null;
        _scrollbarUpdateHoverDuringScroll();
    });
}

function _scrollbarUpdate() {
    var track = document.querySelector('.custom-scroll-track');
    var thumb = document.querySelector('.custom-scroll-thumb');
    var scrollEl = _scrollbarScrollEl;
    var sidebar = document.getElementById('sidebar_container');
    if (!track || !thumb || !scrollEl || !sidebar) return;

    var scrollTop    = scrollEl.scrollTop;
    var scrollHeight = scrollEl.scrollHeight;
    var clientHeight = scrollEl.clientHeight;

    if (scrollHeight <= clientHeight) {
        track.classList.remove('visible');
        return;
    }

    var ratio     = clientHeight / scrollHeight;
    var thumbH    = Math.max(32, ratio * clientHeight);
    var maxThumbY = clientHeight - thumbH;
    var thumbY    = (scrollTop / (scrollHeight - clientHeight)) * maxThumbY;

    thumb.style.height    = thumbH + 'px';
    thumb.style.transform = 'translateY(' + thumbY + 'px)';

    var rect        = scrollEl.getBoundingClientRect();
    var sidebarRect = sidebar.getBoundingClientRect();

    track.style.top    = (rect.top - sidebarRect.top) + 'px';
    track.style.height = clientHeight + 'px';
    track.style.right  = 'auto';
    track.style.left   = (rect.right - sidebarRect.left - 10 - 2) + 'px';
}

function _scrollbarSetHover(item) {
    if (item === _scrollbarHoveredItem) return;
    if (_scrollbarHoveredItem) _scrollbarHoveredItem.classList.remove('hover');
    _scrollbarHoveredItem = item;
    if (_scrollbarHoveredItem) _scrollbarHoveredItem.classList.add('hover');
}

function _scrollbarClearHover() {
    _scrollbarSetHover(null);
}

function _scrollbarUpdateHoverDuringScroll() {
    if (!_scrollbarScrollEl || !_scrollbarScrollEl.classList.contains('is-scrolling')) return;
    // Если курсор вне области скролла – не обновляем ховер
    var scrollRect = _scrollbarScrollEl.getBoundingClientRect();
    if (_globalMouseX < scrollRect.left || _globalMouseX > scrollRect.right ||
        _globalMouseY < scrollRect.top || _globalMouseY > scrollRect.bottom) {
        _scrollbarClearHover();
        return;
    }
    var el = document.elementFromPoint(_globalMouseX, _globalMouseY);
    var item = el ? el.closest('.chat-item') : null;
    _scrollbarSetHover(item);
}

function initChatListScrollbar() {
    var scrollEl = document.querySelector('#sidebar_container > div:has(.chat-list-container)');
    var sidebar  = document.getElementById('sidebar_container');

    if (!scrollEl || !sidebar) { setTimeout(initChatListScrollbar, 100); return; }
    if (sidebar.querySelector('.custom-scroll-track')) return;

    _scrollbarScrollEl = scrollEl;

    var track = document.createElement('div');
    track.className = 'custom-scroll-track';
    var thumb = document.createElement('div');
    thumb.className = 'custom-scroll-thumb';
    track.appendChild(thumb);
    sidebar.appendChild(track);

    function show() {
        _scrollbarUpdate();
        track.classList.add('visible');
    }

    function scheduleHide() {
        clearTimeout(_scrollbarFadeTimer);
        _scrollbarFadeTimer = setTimeout(function() {
            if (!scrollEl.matches(':hover') && !thumb.matches(':hover')) {
                track.classList.remove('visible');
            }
        }, 300);
    }

    scrollEl.addEventListener('scroll', function() {
        show();
        scheduleHide();

        if (!scrollEl.classList.contains('is-scrolling')) {
            scrollEl.classList.add('is-scrolling');
        }

        // Планируем обновление ховера при следующем кадре
        _scheduleHoverUpdate();

        clearTimeout(_scrollbarPointerTimer);
        _scrollbarPointerTimer = setTimeout(function() {
            scrollEl.classList.remove('is-scrolling');
            _scrollbarClearHover(); // убираем все кастомные ховеры после скролла
            // Также отменяем запланированное обновление, если оно было
            if (_updateHoverRafId) {
                cancelAnimationFrame(_updateHoverRafId);
                _updateHoverRafId = null;
            }
        }, 150);
    }, { passive: true });

    scrollEl.addEventListener('mouseenter', function(e) {
        _globalMouseX = e.clientX;
        _globalMouseY = e.clientY;
        show();
        if (scrollEl.classList.contains('is-scrolling')) {
            _scheduleHoverUpdate();
        }
    });

    scrollEl.addEventListener('mouseleave', function() {
        scheduleHide();
        scrollEl.classList.remove('is-scrolling');
        _scrollbarClearHover();
        clearTimeout(_scrollbarPointerTimer);
        if (_updateHoverRafId) {
            cancelAnimationFrame(_updateHoverRafId);
            _updateHoverRafId = null;
        }
    });

    thumb.addEventListener('mouseenter', function() {
        clearTimeout(_scrollbarFadeTimer);
        thumb.classList.add('hovered');
        track.classList.add('visible');
    });
    thumb.addEventListener('mouseleave', function() {
        thumb.classList.remove('hovered');
        scheduleHide();
    });

    new ResizeObserver(_scrollbarUpdate).observe(scrollEl);
    _scrollbarUpdate();
}

initChatListScrollbar();