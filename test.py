# test_changes.py
import sys

def test_imports():
    print("🔍 Тестирование импортов...")
    
    try:
        from container import container
        print("✅ container импортирован")
        
        from services.model_service import ModelService
        print("✅ ModelService импортирован")
        
        from handlers import ui_handlers
        print("✅ ui_handlers импортирован")
        
        # Пробуем получить сервис модели
        model_service = container.get_model_service()
        print("✅ ModelService получен из контейнера")
        
        print("\n✅ Все импорты работают корректно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)