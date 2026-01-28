import requests
import time
import json

def test_api():
    """Тестирует API endpoint"""
    print("🔍 Тестирование API endpoint...")
    
    # Даем время серверу запуститься
    time.sleep(2)
    
    url = "http://127.0.0.1:7860/custom/chat-list"
    
    try:
        response = requests.get(url)
        print(f"📊 Статус: {response.status_code}")
        print(f"📄 Заголовки: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ Успешно! Получено {len(data)} чатов")
                for i, chat in enumerate(data[:3]):  # Показываем первые 3
                    print(f"  {i+1}. {chat['name']} (ID: {chat['id']})")
            except json.JSONDecodeError:
                print(f"❌ Ошибка парсинга JSON: {response.text[:200]}")
        else:
            print(f"❌ Ошибка HTTP: {response.text[:200]}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Не удалось подключиться к серверу. Убедитесь что сервер запущен.")
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")

if __name__ == "__main__":
    test_api()