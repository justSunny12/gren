# ui/resource_loader.py
import os
from container import container


class ResourceLoader:
    """Загрузчик ресурсов (CSS, JS)."""

    def __init__(self):
        self._logger = None

    @property
    def logger(self):
        if self._logger is None:
            self._logger = container.get_logger()
        return self._logger

    def load_css(self):
        """Загружает все CSS файлы из css/."""
        css_files = [
            'css/base.css',
            'css/sidebar.css',
            'css/chat_window.css',
            'css/input_area.css',
            'css/modals.css'
        ]

        css_content = ""
        for css_file in css_files:
            try:
                if os.path.exists(css_file):
                    with open(css_file, 'r', encoding='utf-8') as f:
                        css_content += f.read() + "\n"
                else:
                    self.logger.warning("CSS файл не найден: %s", css_file)
            except Exception as e:
                self.logger.error("Ошибка загрузки CSS файла %s: %s", css_file, e)

        return css_content

    def load_js(self):
        """Загружает все JavaScript файлы."""
        js_files = [
            'static/js/config/selectors.js',
            'static/js/modules/utils.js',
            'static/js/modules/delete-modal.js',
            'static/js/modules/rename-modal.js',
            'static/js/modules/settings-modal.js',
            'static/js/modules/chat-list.js',
            'static/js/modules/context-menu.js',
            'static/js/modules/generation-control.js',
            'static/js/main.js'
        ]

        js_content = ""
        for js_file in js_files:
            try:
                if os.path.exists(js_file):
                    with open(js_file, 'r', encoding='utf-8') as f:
                        js_content += f.read() + "\n\n"
                else:
                    self.logger.warning("JS файл не найден: %s", js_file)
            except Exception as e:
                self.logger.error("Ошибка загрузки JS файла %s: %s", js_file, e)

        js_code = f"""
        <script type="text/javascript">
        {js_content}
        </script>
        """
        return js_code