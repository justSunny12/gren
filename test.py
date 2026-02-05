# test_gradio_chat.py
import gradio as gr
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.events.message_events import MessageEvents

async def stream_message(prompt, chat_id, max_tokens, temperature, enable_thinking):
    from handlers import ui_handlers
    async for history, _, dialog_id, chat_list_data in ui_handlers.send_message_stream_handler(
        prompt, chat_id, max_tokens, temperature, enable_thinking
    ):
        yield history, "", dialog_id, chat_list_data

with gr.Blocks() as demo:
    chatbot = gr.Chatbot()
    user_input = gr.Textbox()
    current_dialog_id = gr.State()
    chat_list_data = gr.Textbox(visible=False)
    max_tokens = gr.Slider(minimum=1, maximum=500, value=100)
    temperature = gr.Slider(minimum=0.1, maximum=2.0, value=0.7)
    enable_thinking = gr.Checkbox(False)

    inputs = [user_input, current_dialog_id, max_tokens, temperature, enable_thinking]
    outputs = [chatbot, user_input, current_dialog_id, chat_list_data]

    user_input.submit(stream_message, inputs, outputs)
    gr.Button("Отправить").click(stream_message, inputs, outputs)

if __name__ == "__main__":
    demo.launch()