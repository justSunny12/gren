import os
import fnmatch
from pathlib import Path
import sys

def load_gitignore_patterns(project_root):
    """Загружает шаблоны из .gitignore"""
    gitignore_path = os.path.join(project_root, '.gitignore')
    patterns = []
    
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Пропускаем пустые строки и комментарии
                if not line or line.startswith('#'):
                    continue
                # Нормализуем слэши для текущей ОС
                line = line.replace('/', os.sep)
                patterns.append(line)
    
    return patterns

def should_ignore(path, gitignore_patterns, project_root, script_name):
    """Проверяет, должен ли путь быть проигнорирован"""
    rel_path = os.path.relpath(path, project_root)
    path_obj = Path(path)
    
    # 1. Проверяем .git директорию
    if '.git' in path_obj.parts:
        return True
    
    # 2. Проверяем сам скрипт сбора дампа
    if path_obj.name == script_name:
        return True
    
    # 3. Проверяем .gitignore паттерны
    for pattern in gitignore_patterns:
        # Преобразуем паттерн в формат для fnmatch
        pattern_fnmatch = pattern
        
        # Если паттерн заканчивается на /, значит это директория
        if pattern.endswith('/'):
            pattern_fnmatch = pattern.rstrip('/')
            if path_obj.is_dir() and fnmatch.fnmatch(rel_path, pattern_fnmatch):
                return True
            continue
        
        # Проверяем полный путь
        if '/' in pattern or '\\' in pattern:
            # Паттерн с путем
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            # Проверяем как **/pattern
            if fnmatch.fnmatch(rel_path, '**' + os.sep + pattern):
                return True
        else:
            # Просто имя файла/папки
            if fnmatch.fnmatch(path_obj.name, pattern):
                return True
    
    return False

def collect_project_files(project_root, script_name):
    """Собирает все файлы проекта, исключая .gitignore шаблоны и сам скрипт"""
    gitignore_patterns = load_gitignore_patterns(project_root)
    project_files = []
    
    for root, dirs, files in os.walk(project_root, topdown=True):
        # Фильтруем директории перед обходом
        dirs[:] = [
            d for d in dirs 
            if not should_ignore(os.path.join(root, d), gitignore_patterns, project_root, script_name)
        ]
        
        for file in files:
            file_path = os.path.join(root, file)
            if not should_ignore(file_path, gitignore_patterns, project_root, script_name):
                project_files.append(file_path)
    
    # Сортируем для удобства чтения
    project_files.sort()
    return project_files

def read_file_content(file_path):
    """Читает содержимое файла с правильной кодировкой"""
    try:
        # Пробуем UTF-8
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            # Пробуем cp1251 (Windows Cyrillic)
            with open(file_path, 'r', encoding='cp1251') as f:
                return f.read()
        except:
            # Для бинарных файлов возвращаем пометку
            return "[BINARY FILE - CONTENT NOT READABLE]\n"

def create_project_dump(project_root, output_file='project_dump.txt'):
    """Создает дамп всех файлов проекта"""
    project_root = os.path.abspath(project_root)
    script_name = os.path.basename(__file__)
    
    if not os.path.exists(project_root):
        print(f"❌ Ошибка: Директория '{project_root}' не существует")
        return False
    
    # Удаляем старый дамп если существует
    if os.path.exists(output_file):
        try:
            os.remove(output_file)
            print(f"🗑️  Удален старый дамп: {output_file}")
        except Exception as e:
            print(f"⚠️  Не удалось удалить старый дамп: {e}")
    
    print(f"🔍 Сканируем проект: {project_root}")
    files = collect_project_files(project_root, script_name)
    print(f"📊 Найдено файлов: {len(files)}")
    
    if len(files) == 0:
        print("❌ Нет файлов для обработки")
        return False
    
    print("📝 Создаем дамп...")
    
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for i, file_path in enumerate(files, 1):
            rel_path = os.path.relpath(file_path, project_root)
            
            # Записываем разделитель
            out_f.write(f"\n{'='*80}\n")
            out_f.write(f"### {rel_path}\n")
            out_f.write(f"{'='*80}\n\n")
            
            # Читаем и записываем содержимое
            content = read_file_content(file_path)
            out_f.write(content)
            
            # Выводим прогресс каждые 10 файлов
            if i % 10 == 0:
                print(f"   Обработано файлов: {i}/{len(files)}")
    
    print(f"\n✅ Дамп проекта сохранен в файл: {output_file}")
    print(f"📊 Всего обработано файлов: {len(files)}")
    
    # Показываем краткую статистику
    print("\n📋 Статистика:")
    print(f"   Корень проекта: {project_root}")
    print(f"   Выходной файл: {output_file}")
    print(f"   Скрипт исключен: {script_name}")
    
    # Проверяем размер
    if os.path.exists(output_file):
        size_kb = os.path.getsize(output_file) / 1024
        print(f"   Размер дампа: {size_kb:.2f} KB")
    
    return True

def main():
    """Основная функция - без интерактивности"""
    # Определяем корень проекта (текущая директория)
    project_root = os.getcwd()
    
    # Имя выходного файла
    output_file = 'project_dump.txt'
    
    # Создаем дамп
    success = create_project_dump(project_root, output_file)
    
    if success:
        print(f"\n🎉 Готово! Файл дампа: {output_file}")
        print("📤 Можете отправить этот файл для анализа кода.")
    else:
        print("\n❌ Создание дампа завершилось с ошибкой.")
        sys.exit(1)

if __name__ == "__main__":
    main()
