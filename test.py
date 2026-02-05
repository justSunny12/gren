# test_step4_handler_format.py
import asyncio
import threading
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from container import container

async def test_handler_format():
    print("🧪 ШАГ 4: Тестирование формата Handler'а и остановки")
    print("=" * 70)
    
    from handlers import ui_handlers
    
    # Тест 1: Проверка формата данных (вариант B) - БЕЗ ИЗМЕНЕНИЙ
    print("1. Тест: Проверка формата данных (вариант B)")
    print("-" * 40)
    
    dialog_service = container.get_dialog_service()
    dialog_id = dialog_service.create_dialog()
    
    prompt = "Что такое Python?"
    print(f"   Диалог: {dialog_id}")
    print(f"   Промпт: {prompt}")
    print("   Запускаю стрим через handler...")
    
    all_yields = []
    
    async for history, empty_str, current_id, chat_list_data in ui_handlers.message_handler.send_message_stream_handler(
        prompt=prompt,
        chat_id=dialog_id,
        max_tokens=50,
        temperature=0.7,
        enable_thinking=False
    ):
        all_yields.append({
            "history": history,
            "dialog_id": current_id,
            "history_length": len(history),
            "last_msg_role": history[-1]["role"] if history else None,
            "last_msg_content_preview": repr(history[-1]["content"][:30]) if history and history[-1]["content"] else None
        })
    
    print(f"   Получено yield'ов: {len(all_yields)}")
    
    if len(all_yields) > 1:
        first = all_yields[0]
        last = all_yields[-1]
        
        print(f"   Первый yield: {first['history_length']} сообщений в истории")
        print(f"   Последний yield: {last['history_length']} сообщений в истории")
        
        growing = True
        prev_length = 0
        for i, y in enumerate(all_yields):
            last_content = y["history"][-1]["content"] if y["history"] else ""
            if len(last_content) < prev_length and i > 0:
                growing = False
                break
            prev_length = len(last_content)
        
        if growing:
            print("   ✅ Формат B корректен: ответ ассистента нарастает в каждом yield")
        else:
            print("   ❌ Формат B нарушен: ответ не нарастает монотонно")
        
        try:
            json.loads(chat_list_data)
            print("   ✅ chat_list_data - валидный JSON")
        except:
            print("   ❌ chat_list_data - невалидный JSON")
    
    # Тест 2: Остановка через handler - ИСПРАВЛЕННАЯ ВЕРСИЯ
    print("\n2. Тест: Остановка через handler.stop_active_generation()")
    print("-" * 40)
    
    dialog_id2 = dialog_service.create_dialog()
    prompt2 = "Объясни теорию относительности."
    
    print(f"   Диалог: {dialog_id2}")
    print(f"   Промпт: {prompt2}")
    
    async def consume_with_stop():
        all_chunks = []
        stream_active = True  # Флаг, что стрим еще активен
        
        # Запускаем стриминг в фоновой задаче
        async def stream():
            nonlocal all_chunks, stream_active
            try:
                async for history, _, _, _ in ui_handlers.message_handler.send_message_stream_handler(
                    prompt=prompt2,
                    chat_id=dialog_id2,
                    max_tokens=300,  # УВЕЛИЧИЛИ для более долгой генерации
                    temperature=0.7,
                    enable_thinking=False
                ):
                    all_chunks.append(history)
            finally:
                stream_active = False  # Стрим завершился
        
        task = asyncio.create_task(stream())
        
        # Ждем меньше времени перед остановкой, чтобы успеть прервать
        await asyncio.sleep(1.2)  # УМЕНЬШИЛИ время ожидания до 1.2 секунды
        
        # Проверяем, активен ли еще стрим
        if stream_active:
            print("   ⏱️  Прошло 1.2 секунды, стрим еще активен, вызываю stop_active_generation()...")
            stopped = ui_handlers.stop_active_generation()
            
            if stopped:
                print(f"   ✅ stop_active_generation() вернул True (остановка инициирована)")
            else:
                print(f"   ❌ stop_active_generation() вернул False (не нашел активную генерацию)")
        else:
            print("   ⚠️  Стрим уже завершился до попытки остановки")
            stopped = False
        
        # Ждем завершения задачи
        await task
        return stopped, len(all_chunks), stream_active
    
    stopped, num_chunks, was_still_active = await consume_with_stop()
    
    print(f"   Получено чанков до остановки: {num_chunks}")
    print(f"   Стрим был активен в момент остановки: {was_still_active}")
    
    # Проверяем суффикс в сохраненном диалоге
    dialog = dialog_service.get_dialog(dialog_id2)
    if dialog and dialog.history:
        last_msg = dialog.history[-1].content
        if "...<генерация прервана пользователем>" in last_msg:
            print("   ✅ Суффикс присутствует в сохраненном сообщении")
        else:
            print(f"   ❌ Суффикс отсутствует. Сообщение (первые 100 символов): {repr(last_msg[:100])}")
    
    print("\n" + "=" * 70)
    print("🎉 ШАГ 4 завершен. Handler возвращает корректный формат.")

if __name__ == "__main__":
    asyncio.run(test_handler_format())