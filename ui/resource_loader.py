# ui/resource_loader.py
import os

class ResourceLoader:
    """Загрузчик ресурсов (CSS, JS)"""
    
    @staticmethod
    def load_css():
        """Загружает все CSS файлы из static/css/"""
        css_files = [
            'css/base.css',
            'css/sidebar.css', 
            'css/chat_window.css',
            'css/input_area.css'  # <-- Уже обновлен с generation-buttons-wrapper
        ]
        
        css_content = ""
        
        for css_file in css_files:
            try:
                if os.path.exists(css_file):
                    with open(css_file, 'r', encoding='utf-8') as f:
                        css_content += f.read() + "\n"
                else:
                    print(f"⚠️ CSS файл не найден: {css_file}")
            except Exception as e:
                print(f"⚠️ Ошибка загрузки CSS файла {css_file}: {e}")
        
        return css_content
    
    @staticmethod
    def load_js():
        """Загружает все JavaScript файлы"""
        js_files = [
            'static/js/config/selectors.js',      # 1. Селекторы
            'static/js/modules/utils.js',         # 2. Утилиты
            'static/js/modules/delete-modal.js',  # 3. Модальное окно удаления
            'static/js/modules/rename-modal.js',  # 4. Модальное окно переименования
            'static/js/modules/chat-list.js',     # 5. Список чатов
            'static/js/modules/context-menu.js',  # 6. Контекстное меню
            'static/js/modules/generation-control.js',  # 7. НОВЫЙ: Управление кнопками генерации
            'static/js/main.js'                   # 8. Основной код
        ]
        
        js_content = ""
        for js_file in js_files:
            try:
                if os.path.exists(js_file):
                    with open(js_file, 'r', encoding='utf-8') as f:
                        js_content += f.read() + "\n\n"
                else:
                    print(f"⚠️ JS файл не найден: {js_file}")
            except Exception as e:
                print(f"⚠️ Ошибка загрузки JS файла {js_file}: {e}")
        
        js_code = f"""
        <script type="text/javascript">
        {js_content}
        </script>
        """
        
        return js_code