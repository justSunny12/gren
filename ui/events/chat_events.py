# ui/events/chat_events.py
import gradio as gr
from handlers import ui_handlers

class ChatEvents:

    @staticmethod
    def bind_chat_selection_events(chat_input, chatbot, current_dialog_id, chat_list_data):
        chat_input.input(
            fn=ui_handlers.handle_chat_selection,
            inputs=[chat_input],
            outputs=[chatbot, current_dialog_id, chat_list_data]
        )
        chat_input.change(
            fn=ui_handlers.handle_chat_selection,
            inputs=[chat_input],
            outputs=[chatbot, current_dialog_id, chat_list_data]
        )

    @staticmethod
    def bind_chat_creation_events(create_dialog_btn, chatbot, user_input,
                                  current_dialog_id, js_trigger, chat_list_data):
        create_dialog_btn.click(
            fn=ui_handlers.create_chat_with_js_handler,
            inputs=[],
            outputs=[chatbot, user_input, current_dialog_id, js_trigger, chat_list_data]
        )

    @staticmethod
    def bind_settings_button_events(settings_btn, settings_data):
        """При нажатии на кнопку настроек – читаем данные из settings_data и показываем модалку.
           НИКАКОГО ВЫЗОВА PYTHON!"""
        # Сначала сохраняем настройки в глобальную переменную при их обновлении
        settings_data.change(
            fn=None,
            inputs=[settings_data],
            outputs=[],
            js="""
            (data) => {
                try {
                    window.appSettings = data;
                    console.log('✅ Настройки кэшированы:', data);
                } catch (e) {
                    console.error('Ошибка кэширования настроек:', e);
                }
                return [];
            }
            """
        )

        # Клик по кнопке – используем window.appSettings
        settings_btn.click(
            fn=None,  # БЕЗ Python-функции!
            inputs=[],
            outputs=[],
            js="""
            () => {
                try {
                    if (!window.appSettings) {
                        console.error('Настройки ещё не загружены');
                        return [];
                    }
                    if (window.showSettingsModal) {
                        window.showSettingsModal(window.appSettings);
                    } else {
                        console.error('showSettingsModal not defined');
                    }
                } catch (e) {
                    console.error('Error opening settings modal:', e);
                }
                return [];
            }
            """
        )

    @staticmethod
    def bind_chat_list_update(chat_list_data):
        return chat_list_data.change(
            fn=None,
            inputs=[chat_list_data],
            outputs=[],
            js="""
            (data) => {
                try {
                    const parsed = JSON.parse(data);
                    const scrollTarget = parsed._scroll_target || 'none';
                    if (window.renderChatList) {
                        window.renderChatList(parsed, scrollTarget);
                    }
                } catch (e) {
                    console.error('Ошибка рендеринга списка чатов:', e);
                }
                return [];
            }
            """
        )