# test_streaming_fix.py
import sys
sys.path.append('.')
from models.dialog import Dialog
from models.enums import MessageRole
import time

def test_streaming_with_cache():
    """Тест, что кэширование не ломает стриминг"""
    print("🧪 Тестирование стриминга с кэшированием...")
    
    # Создаем диалог с историей
    dialog = Dialog(id="stream_test", name="Тест стриминга")
    
    # Добавляем сообщение пользователя
    dialog.add_message(MessageRole.USER, "Привет!")
    
    # Получаем базовую историю (кэшируется)
    base_history = dialog.to_ui_format()
    print(f"   Базовая история: {len(base_history)} сообщений")
    
    # Имитируем стриминг - несколько чанков
    accumulated = ""
    chunks = ["При", "вет, ", "как ", "дела?"]
    
    for i, chunk in enumerate(chunks):
        accumulated += chunk
        
        # Способ 1: Старый (неправильный) - модифицирует кэш
        # wrong_history = base_history  # ЭТО ОПАСНО!
        # wrong_history.append({"role": "assistant", "content": accumulated})
        
        # Способ 2: Новый (правильный) - создаём копию
        correct_history = list(base_history)  # Копируем!
        correct_history.append({
            "role": MessageRole.ASSISTANT.value,
            "content": accumulated
        })
        
        print(f"   Чанк {i+1}: '{chunk}' -> История: {len(correct_history)} сообщений")
        print(f"      Накопленный ответ: '{accumulated}'")
        
        # Проверяем, что базовая история не изменилась
        assert len(base_history) == 1, f"❌ Базовая история изменилась: {len(base_history)}"
    
    # В конце добавляем финальное сообщение в диалог
    dialog.add_message(MessageRole.ASSISTANT, accumulated)
    final_history = dialog.to_ui_format()
    
    print(f"\n   Финальная история: {len(final_history)} сообщений")
    assert len(final_history) == 2, f"❌ Финальная история должна содержать 2 сообщения"
    assert final_history[-1]["content"] == "Привет, как дела?", "❌ Содержимое не совпадает"
    
    print("\n✅ Стриминг работает корректно с кэшированием!")
    return True

def test_cache_integrity():
    """Тест целостности кэша при стриминге"""
    print("\n🔒 Тест целостности кэша...")
    
    dialog = Dialog(id="cache_test", name="Тест кэша")
    
    # Добавляем начальные сообщения
    dialog.add_message(MessageRole.USER, "Вопрос 1")
    dialog.add_message(MessageRole.ASSISTANT, "Ответ 1")
    
    # Получаем историю (кэшируется)
    history1 = dialog.to_ui_format()
    print(f"   История 1: {len(history1)} сообщений")
    
    # Имитируем новый стриминг (не добавляя в диалог)
    base_history = dialog.to_ui_format()
    
    # Создаём временные истории для стриминга
    streaming_histories = []
    chunks = ["Ча", "сть ", "от", "вета"]
    accumulated = ""
    
    for chunk in chunks:
        accumulated += chunk
        temp_history = list(base_history)  # Копируем!
        temp_history.append({
            "role": MessageRole.ASSISTANT.value,
            "content": accumulated
        })
        streaming_histories.append(temp_history)
    
    print(f"   Создано {len(streaming_histories)} временных историй для стриминга")
    
    # Проверяем, что кэш не повреждён
    history2 = dialog.to_ui_format()
    print(f"   История 2 (после стриминга): {len(history2)} сообщений")
    
    # Они должны быть одним и тем же объектом (кэш)
    assert history1 is history2, "❌ Кэш был повреждён стримингом!"
    assert len(history1) == 2, f"❌ Кэш содержит неверное количество сообщений"
    
    # Проверяем, что временные истории не повлияли на диалог
    for i, temp_history in enumerate(streaming_histories):
        assert len(temp_history) == 3, f"❌ Временная история {i} неправильной длины"
        assert temp_history is not history1, f"❌ Временная история {i} ссылается на кэш"
    
    print("✅ Кэш остаётся неизменным во время стриминга!")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЯ СТРИМИНГА")
    print("=" * 60)
    
    try:
        test_streaming_with_cache()
        test_cache_integrity()
        
        print("\n" + "=" * 60)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Стриминг работает с кэшированием")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)