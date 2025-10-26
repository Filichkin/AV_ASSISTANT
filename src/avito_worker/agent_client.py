"""Клиент для работы с RAG-агентом."""

from loguru import logger

from agent.gigachat.ai_agent import build_agent
from agent.gigachat.mcp_client import McpClient


class AgentClient:
    """Клиент для работы с RAG-агентом на основе GigaChat и MCP."""

    def __init__(
        self,
        mcp_server_url: str,
        mcp_transport: str,
        mcp_rag_tool_name: str,
        gigachat_model: str,
        gigachat_temperature: float,
        gigachat_scope: str,
        gigachat_credentials: str,
        gigachat_verify_ssl: bool = True,
        max_tokens: int = 1000
    ):
        """Инициализация клиента агента.

        Args:
            mcp_server_url: URL MCP сервера
            mcp_transport: Тип транспорта (обычно 'sse')
            mcp_rag_tool_name: Имя RAG tool в MCP
            gigachat_model: Модель GigaChat
            gigachat_temperature: Температура генерации
            gigachat_scope: Scope для GigaChat
            gigachat_credentials: Credentials для GigaChat
            gigachat_verify_ssl: Проверять SSL сертификаты
            max_tokens: Максимальное количество токенов в ответе
        """
        self.mcp_server_url = mcp_server_url
        self.mcp_transport = mcp_transport
        self.mcp_rag_tool_name = mcp_rag_tool_name
        self.gigachat_model = gigachat_model
        self.gigachat_temperature = gigachat_temperature
        self.gigachat_scope = gigachat_scope
        self.gigachat_credentials = gigachat_credentials
        self.gigachat_verify_ssl = gigachat_verify_ssl
        self.max_tokens = max_tokens
        self._mcp_client = None
        self._agent = None
        self._astream_answer = None

    async def __aenter__(self):
        """Подключение к MCP серверу и инициализация агента."""
        self._mcp_client = McpClient(
            url=self.mcp_server_url,
            transport=self.mcp_transport
        )
        await self._mcp_client.__aenter__()

        # Создаем агента
        self._agent, self._astream_answer = build_agent(
            mcp=self._mcp_client,
            rag_tool_name=self.mcp_rag_tool_name,
            model_name=self.gigachat_model,
            temperature=self.gigachat_temperature,
            scope=self.gigachat_scope,
            credentials=self.gigachat_credentials,
            verify_ssl=self.gigachat_verify_ssl,
            max_tokens=self.max_tokens,
        )
        logger.info('Агент успешно инициализирован')
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Отключение от MCP сервера."""
        if self._mcp_client:
            await self._mcp_client.__aexit__(exc_type, exc_val, exc_tb)
            logger.info('Агент отключен')

    async def get_answer(self, user_message: str) -> str:
        """Получить ответ от агента на сообщение пользователя.

        Args:
            user_message: Сообщение пользователя

        Returns:
            Ответ агента

        Raises:
            RuntimeError: При ошибке получения ответа
        """
        if not self._astream_answer:
            raise RuntimeError('Агент не инициализирован')

        try:
            logger.info(f'Запрос к агенту: {user_message[:50]}...')
            answer_parts = []

            # Стримим ответ от агента
            async for chunk in self._astream_answer(user_message):
                answer_parts.append(chunk)

            answer = ''.join(answer_parts).strip()
            if not answer:
                logger.warning('Агент вернул пустой ответ')
                answer = (
                    'Извините, не удалось получить ответ. '
                    'Попробуйте переформулировать вопрос.'
                )

            logger.info(f'Ответ агента получен (длина: {len(answer)} симв.)')
            return answer
        except Exception as e:
            logger.error(f'Ошибка при получении ответа от агента: {e}')
            raise RuntimeError(f'Ошибка агента: {e}')
