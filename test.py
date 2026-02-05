# 1. Проверим импорты
from ui import create_main_ui
print('✅ create_main_ui импортирована')

# 2. Проверим ресурсы
from ui.resource_loader import ResourceLoader
loader = ResourceLoader()
css = loader.load_css()
js = loader.load_js()
print(f'✅ Ресурсы загружены: CSS={len(css)} символов, JS={len(js)} символов')

# 3. Проверим события
from ui.events import EventBinder
binder = EventBinder()
print(f'✅ EventBinder создан: {binder}')