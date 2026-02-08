# test_integration.py
import sys
sys.path.insert(0, '.')

from container import container

def test_integration():
    """Интеграционный тест контейнера и медиатора"""
    print("Интеграционное тестирование...")
    
    # Получаем медиатор через контейнер
    mediator = container.get("ui_mediator")
    assert mediator is not None, "Медиатор должен быть доступен через контейнер"
    print("✓ Медиатор загружен через контейнер")
    
    # Проверяем, что медиатор может получить данные
    chat_list_data = mediator.get_chat_list_data()
    assert isinstance(chat_list_data, str), "Данные должны быть строкой (JSON)"
    print("✓ Медиатор может получать данные списка чатов")
    
    # Проверяем другие сервисы
    config = container.get_config()
    assert config is not None, "Конфигурация должна быть доступна"
    print("✓ Все сервисы доступны через контейнер")
    
    print("Интеграционный тест пройден успешно!")

if __name__ == "__main__":
    test_integration()