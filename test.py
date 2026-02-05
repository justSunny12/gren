# test_fixed_chain.py
import gradio as gr
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from container import container

def clear_input_and_save_prompt(prompt):
    """Очищает поле ввода и возвращает сохраненный промпт"""
    print(f"🧹 Очищаю поле ввода, сохраняю промпт: '{prompt}'")
    return "", prompt

async def stream_response_only(saved_prompt, chat_id, max_tokens, temperature, enable_thinking):
    """Генератор для чатбота, использует сохраненный промпт"""
    from handlers import ui_handlers
    
    if not saved_prompt or saved_prompt.strip() == "":
        print("⚠️ Внимание: промпт пустой!")
        yield [], chat_id, "[]"
        return
    
    print(f"🚀 Начинаю стриминг для сохраненного промпта: '{saved_prompt}'")
    
    try:
        chunk_count = 0
        async for history, _, dialog_id, chat_list_data in ui_handlers.send_message_stream_handler(
            saved_prompt, chat_id, max_tokens, temperature, enable_thinking
        ):
            chunk_count += 1
            if chunk_count == 1:
                print(f"✅ Получен первый чанк, начинаю поток...")
            
            # Возвращаем только историю, ID диалога и список чатов
            yield history, dialog_id, chat_list_data
        
        print(f"🎯 Стриминг завершен, всего чанков: {chunk_count}")
        
    except Exception as e:
        print(f"❌ Ошибка в stream_response_only: {e}")
        import traceback
        traceback.print_exc()
        yield [], chat_id, "[]"

def main():
    # Инициализируем модель
    model_service = container.get_model_service()
    if not model_service.is_initialized():
        print("⚙️ Инициализация модели...")
        model_service.initialize()
    
    with gr.Blocks(title="Тест: исправленная цепочка", theme="soft") as demo:
        gr.Markdown("# 🚀 Исправленная цепочка событий")
        gr.Markdown("Теперь промпт сохраняется в состоянии и передается правильно")
        
        chatbot = gr.Chatbot(
            label="Чат",
            height=400,
            avatar_images=(None, "https://avatars.githubusercontent.com/u/1024")
        )
        
        with gr.Row():
            user_input = gr.Textbox(
                placeholder="Введите сообщение...",
                show_label=False,
                scale=9,
                elem_id="fixed_chain_input"
            )
            submit_btn = gr.Button("Отправить", variant="primary", scale=1)
        
        current_dialog_id = gr.State()
        chat_list_data = gr.Textbox(visible=False)
        
        # Скрытое состояние для сохранения промпта
        saved_prompt = gr.State()
        
        # Параметры
        max_tokens = gr.Slider(
            minimum=50, maximum=200, value=100, step=25,
            label="Максимальное количество токенов"
        )
        temperature = gr.Slider(
            minimum=0.1, maximum=1.5, value=0.7, step=0.1,
            label="Температура"
        )
        enable_thinking = gr.Checkbox(
            label="🧠 Глубокое размышление",
            value=False
        )
        
        gr.Markdown("### 📋 Как работает:")
        gr.Markdown("""
        1. **При отправке:** промпт сохраняется в скрытом состоянии `saved_prompt`
        2. **Поле ввода:** мгновенно очищается
        3. **Стриминг:** использует сохраненный промпт из `saved_prompt`
        4. **Во время генерации:** можно вводить новый текст
        """)
        
        # Цепочка событий
        submit_btn.click(
            fn=clear_input_and_save_prompt,
            inputs=[user_input],
            outputs=[user_input, saved_prompt],
            api_name="clear_and_save"
        ).then(
            fn=stream_response_only,
            inputs=[saved_prompt, current_dialog_id, max_tokens, temperature, enable_thinking],
            outputs=[chatbot, current_dialog_id, chat_list_data],
            api_name="stream_with_saved"
        )
        
        user_input.submit(
            fn=clear_input_and_save_prompt,
            inputs=[user_input],
            outputs=[user_input, saved_prompt]
        ).then(
            fn=stream_response_only,
            inputs=[saved_prompt, current_dialog_id, max_tokens, temperature, enable_thinking],
            outputs=[chatbot, current_dialog_id, chat_list_data]
        )
    
    return demo

if __name__ == "__main__":
    print("🚀 Запуск теста исправленной цепочки...")
    print("📌 Откройте http://localhost:7864 в браузере")
    
    demo = main()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7864,
        share=False,
        show_error=True
    )