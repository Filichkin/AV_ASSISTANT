import asyncio
from typing import AsyncGenerator
import sys


import gradio as gr
from loguru import logger

from agent.gigachat.ai_agent import build_agent
from agent.gigachat.mcp_client import McpClient
from config import settings


class ChatWithAvito:
    """Gradio interface for Avito RAG agent chat."""

    def __init__(self):
        self.chat_history = []
        self.setup_logging()

    def setup_logging(self):
        """Configure logging for the application."""
        logger.remove()
        logger.add(
            sys.stderr,
            format='<green>{time:YYYY-MM-DD HH:mm:ss}</green> | '
                   '<level>{level: <8}</level> | '
                   '<cyan>{name}</cyan>:<cyan>{function}</cyan>:'
                   '<cyan>{line}</cyan> - '
                   '<level>{message}</level>',
            level='INFO'
        )

    async def stream_agent_response(
            self, query: str
    ) -> AsyncGenerator[str, None]:
        """
        Stream agent response with proper MCP client context management.

        Args:
            query: User query string

        Yields:
            str: Chunks of agent response
        """
        if not query.strip():
            yield 'Пожалуйста, введите ваш вопрос.'
            return

        logger.info(f'Starting agent response for query: {query[:50]}...')

        try:
            async with McpClient(
                url=settings.MCP_SERVER_URL,
                transport=settings.MCP_TRANSPORT
            ) as mcp:
                agent, astream_answer = build_agent(
                    mcp=mcp,
                    rag_tool_name=settings.MCP_RAG_TOOL_NAME,
                    model_name=settings.GIGACHAT_MODEL,
                    temperature=settings.GIGACHAT_TEMPERATURE,
                    scope=settings.GIGACHAT_SCOPE,
                    credentials=settings.GIGACHAT_CREDENTIALS,
                    verify_ssl=settings.GIGACHAT_VERIFY_SSL,
                )

                logger.info(
                    'Agent built successfully, starting response stream...'
                )

                full_response = ''
                async for chunk in astream_answer(query):
                    full_response += chunk
                    yield chunk

                logger.info(
                    f'Agent response completed. Total length: '
                    f'{len(full_response)} chars'
                )

        except Exception as e:
            error_msg = f'Ошибка при получении ответа от агента: {str(e)}'
            logger.error(error_msg)
            yield error_msg

    async def process_query(
            self, query: str, history: list
    ) -> AsyncGenerator[tuple[str, list], None]:
        """
        Process user query and return response with updated history.

        Args:
            query: User input query
            history: Current chat history

        Yields:
            tuple: (response, updated_history)
        """
        if not query.strip():
            yield '', history
            return

        # Create a copy of history to avoid modifying the original
        current_history = history.copy()

        # Add user message to history
        current_history.append([query, None])

        # Stream the response
        response_chunks = []
        async for chunk in self.stream_agent_response(query):
            response_chunks.append(chunk)
            # Update history with partial response for real-time display
            current_history[-1][1] = ''.join(response_chunks)
            yield '', current_history

        # Final response
        final_response = ''.join(response_chunks)
        current_history[-1][1] = final_response

        yield '', current_history

    def create_interface(self) -> gr.Blocks:
        """Create and configure Gradio interface."""

        with gr.Blocks(
            title='Avito RAG Agent Chat',
            theme=gr.themes.Soft(),
            css="""
            .gradio-container {
                max-width: 1200px !important;
                margin: auto !important;
            }
            .chat-message {
                padding: 10px;
                margin: 5px 0;
                border-radius: 8px;
            }
            """
        ) as interface:

            gr.Markdown(
                '# 🤖 Avito RAG Agent Chat\n'
                'Задавайте вопросы о ноутбуках и получайте ответы на основе '
                'базы знаний Avito.'
            )

            with gr.Row():
                with gr.Column(scale=3):
                    chatbot = gr.Chatbot(
                        label='Чат с агентом',
                        height=500,
                        show_label=True,
                        container=True,
                        bubble_full_width=False
                    )

                    with gr.Row():
                        msg_input = gr.Textbox(
                            label='Ваш вопрос',
                            placeholder=(
                                'Например: Найди игровой ноутбук до '
                                '100000 рублей'
                            ),
                            lines=2,
                            scale=4
                        )
                        send_btn = gr.Button(
                            'Отправить', variant='primary', scale=1
                        )

                    with gr.Row():
                        clear_btn = gr.Button(
                            'Очистить чат', variant='secondary'
                        )
                        status_text = gr.Textbox(
                            label='Статус',
                            value='Готов к работе',
                            interactive=False
                        )

            # Event handlers
            def submit_message(message, history):
                """Handle message submission."""
                if not message.strip():
                    return '', history, 'Введите вопрос для отправки'

                return '', history, 'Обрабатываю запрос...'

            def clear_chat():
                """Clear chat history."""
                return [], 'Чат очищен'

            # Connect events
            clear_btn.click(
                fn=clear_chat,
                outputs=[chatbot, status_text]
            )

            # Async processing for actual agent responses
            def process_async(message, history):
                """Process message asynchronously."""
                if not message.strip():
                    return '', history, 'Введите вопрос для отправки'

                # Use asyncio to run the async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    async def async_process():
                        final_history = history
                        async for response, updated_history in (
                            self.process_query(message, history)
                        ):
                            final_history = updated_history
                        return '', final_history, 'Готов к работе'

                    return loop.run_until_complete(async_process())
                finally:
                    loop.close()

            # Connect the async processing
            send_btn.click(
                fn=process_async,
                inputs=[msg_input, chatbot],
                outputs=[msg_input, chatbot, status_text],
                queue=True
            )

            msg_input.submit(
                fn=process_async,
                inputs=[msg_input, chatbot],
                outputs=[msg_input, chatbot, status_text],
                queue=True
            )

            # Add examples
            gr.Examples(
                examples=[
                    'Найди игровой ноутбук до 100000 рублей',
                    'Покажи MacBook Air с процессором M2',
                    'Нужен ноутбук для учебы с 16 ГБ оперативной памяти',
                    'Найди бюджетный ноутбук с SSD диском',
                    'Покажи ноутбуки с видеокартой RTX 4060'
                ],
                inputs=msg_input,
                label='Примеры вопросов'
            )

            # Add footer
            gr.Markdown(
                '---\n'
                '**Примечание:** '
                'Ответы основаны на данных из базы знаний Avito. '
                'Агент использует '
                'RAG (Retrieval-Augmented Generation) для поиска '
                'релевантной информации.'
            )

        return interface

    def launch(self, **kwargs):
        """Launch the Gradio interface."""
        interface = self.create_interface()

        default_kwargs = {
            'server_name': '0.0.0.0',
            'server_port': settings.FRONTEND_PORT,
            'share': False,
            'debug': True,
            'show_error': True
        }

        default_kwargs.update(kwargs)

        logger.info(
            f'Launching Avito RAG Agent Chat on port '
            f'{default_kwargs["server_port"]}'
        )

        return interface.launch(**default_kwargs)


def main():
    """Main function to run the chat interface."""
    try:
        chat_app = ChatWithAvito()
        chat_app.launch()
    except KeyboardInterrupt:
        logger.info('Application stopped by user')
    except Exception as e:
        logger.error(f'Failed to start application: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
