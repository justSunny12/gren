# ui/resource_loader.py
import os

class ResourceLoader:
    """Загрузчик ресурсов (CSS, JS)."""

    @staticmethod
    def load_css():
        """Загружает все CSS файлы из css/."""
        
        from container import container
        logger = container.get_logger()
        
        css_files = [
            'css/base.css',
            'css/sidebar.css',
            'css/chat_window.css',
            'css/input_area.css',
            'css/modals.css'          # <-- добавлено
        ]

        css_content = ""
        for css_file in css_files:
            try:
                if os.path.exists(css_file):
                    with open(css_file, 'r', encoding='utf-8') as f:
                        css_content += f.read() + "\n"
                else:
                    logger.warning("CSS файл не найден: %s", css_file)
            except Exception as e:
                logger.error("Ошибка загрузки CSS файла %s: %s", css_file, e)

        return css_content

    @staticmethod
    def load_js():
        """Загружает все JavaScript файлы."""
        
        from container import container
        logger = container.get_logger()
        
        js_files = [
            'static/js/config/selectors.js',      # 1. Селекторы
            'static/js/modules/utils.js',         # 2. Утилиты
            'static/js/modules/delete-modal.js',  # 3. Модальное окно удаления
            'static/js/modules/rename-modal.js',  # 4. Модальное окно переименования
            'static/js/modules/settings-modal.js',# 5. Модальное окно настроек (НОВОЕ)
            'static/js/modules/chat-list.js',     # 6. Список чатов
            'static/js/modules/context-menu.js',  # 7. Контекстное меню
            'static/js/modules/generation-control.js', # 8. Управление генерацией
            'static/js/main.js'                  # 9. Основной код
        ]

        js_content = ""
        for js_file in js_files:
            try:
                if os.path.exists(js_file):
                    with open(js_file, 'r', encoding='utf-8') as f:
                        js_content += f.read() + "\n\n"
                else:
                    logger.warning("JS файл не найден: %s", js_file)
            except Exception as e:
                logger.error("Ошибка загрузки JS файла %s: %s", js_file, e)

        js_code = f"""
        <script type="text/javascript">
        {js_content}
        </script>
        """
        return js_code