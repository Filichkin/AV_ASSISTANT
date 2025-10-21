"""Главный worker для обработки сообщений из Avito."""

import asyncio
import signal
import sys
from datetime import datetime
from typing import Optional

from loguru import logger

from config import settings
from src.common.redis_client import RedisClient
from src.common.models import AvitoMessage, DialogState
from src.avito_worker.avito_api import AvitoAPIClient
from src.avito_worker.agent_client import AgentClient


class AvitoWorker:
    """Worker для обработки сообщений из мессенджера Avito."""

    def __init__(
        self,
        redis_client: RedisClient,
        avito_client: AvitoAPIClient,
        poll_interval: int = 30
    ):
        """Инициализация worker.

        Args:
            redis_client: Клиент Redis
            avito_client: Клиент Avito API
            poll_interval: Интервал опроса API в секундах
        """
        self.redis = redis_client
        self.avito = avito_client
        self.poll_interval = poll_interval
        self._running = False
        self._agent_client: Optional[AgentClient] = None

    async def start(self):
        """Запустить worker."""
        logger.info('Запуск Avito Worker...')
        self._running = True

        # Инициализируем агента
        self._agent_client = AgentClient(
            mcp_server_url=settings.MCP_SERVER_URL,
            mcp_transport=settings.MCP_TRANSPORT,
            mcp_rag_tool_name=settings.MCP_RAG_TOOL_NAME,
            gigachat_model=settings.GIGACHAT_MODEL,
            gigachat_temperature=settings.GIGACHAT_TEMPERATURE,
            gigachat_scope=settings.GIGACHAT_SCOPE,
            gigachat_credentials=settings.GIGACHAT_CREDENTIALS,
            gigachat_verify_ssl=settings.GIGACHAT_VERIFY_SSL,
        )
        await self._agent_client.__aenter__()

        # Запускаем два процесса параллельно
        await asyncio.gather(
            self._poll_avito_loop(),
            self._process_messages_loop(),
        )

    async def stop(self):
        """Остановить worker."""
        logger.info('Остановка Avito Worker...')
        self._running = False
        if self._agent_client:
            await self._agent_client.__aexit__(None, None, None)

    async def _poll_avito_loop(self):
        """Цикл опроса Avito API каждые N секунд."""
        logger.info(
            f'Запущен цикл опроса Avito API '
            f'(интервал: {self.poll_interval}с)'
        )

        while self._running:
            try:
                # Получаем непрочитанные чаты
                unread_chats = await self.avito.get_unread_chats()

                total_messages = 0

                # Для каждого чата получаем новые сообщения
                for chat in unread_chats:
                    chat_id = chat.get('id')
                    if not chat_id:
                        continue

                    # Получаем последние сообщения из чата
                    messages = await self.avito.get_chat_messages(
                        chat_id=chat_id,
                        limit=50  # Получаем до 50 последних сообщений
                    )

                    # Фильтруем только входящие непрочитанные сообщения
                    for msg_data in messages:
                        # Пропускаем исходящие и уже прочитанные
                        if msg_data.get('direction') != 'in':
                            continue
                        if msg_data.get('is_read', False):
                            continue

                        # Извлекаем текст из content
                        content = msg_data.get('content', {})
                        text = content.get('text', '')

                        if not text:
                            # Пропускаем сообщения без текста
                            continue

                        # Создаём сообщение для очереди
                        message = AvitoMessage(
                            message_id=msg_data['id'],
                            chat_id=chat_id,
                            user_id=str(msg_data.get('author_id', '')),
                            text=text,
                        )
                        await self.redis.enqueue_message(message)
                        total_messages += 1

                # Обновляем статистику
                await self._update_stats(
                    last_poll_time=datetime.utcnow()
                )

                if total_messages > 0:
                    logger.info(
                        f'Добавлено {total_messages} '
                        f'сообщений в очередь из {len(unread_chats)} чатов'
                    )

            except Exception as e:
                logger.error(f'Ошибка при опросе Avito API: {e}')
                await self._update_stats(last_error=str(e))

            # Ждем перед следующим опросом
            await asyncio.sleep(self.poll_interval)

    async def _process_messages_loop(self):
        """Цикл обработки сообщений из очереди."""
        logger.info('Запущен цикл обработки сообщений')

        while self._running:
            try:
                # Извлекаем сообщение из очереди
                message = await self.redis.dequeue_message()
                if not message:
                    # Очередь пуста, ждем немного
                    await asyncio.sleep(1)
                    continue

                # Обрабатываем сообщение
                await self._process_message(message)

            except Exception as e:
                logger.error(f'Ошибка в цикле обработки: {e}')
                await asyncio.sleep(1)

    async def _process_message(self, message: AvitoMessage):
        """Обработать одно сообщение.

        Args:
            message: Сообщение для обработки
        """
        try:
            logger.info(
                f'Обработка сообщения {message.message_id} '
                f'из чата {message.chat_id}'
            )

            # Обновляем состояние диалога
            dialog_state = await self.redis.get_dialog_state(
                message.chat_id
            )
            if not dialog_state:
                dialog_state = DialogState(
                    chat_id=message.chat_id,
                    user_id=message.user_id,
                )
            dialog_state.last_message_id = message.message_id
            dialog_state.last_activity = datetime.utcnow()
            dialog_state.message_count += 1
            await self.redis.save_dialog_state(dialog_state)

            # Получаем ответ от агента
            answer = await self._agent_client.get_answer(message.text)

            # Отправляем ответ в Avito
            await self.avito.send_message(
                chat_id=message.chat_id,
                text=answer
            )

            # Отмечаем чат как прочитанный
            await self.avito.mark_chat_as_read(message.chat_id)

            # Помечаем как обработанное
            await self.redis.complete_message(message.message_id)

            logger.info(
                f'Сообщение {message.message_id} '
                f'успешно обработано'
            )

            # Обновляем статистику
            await self._update_stats()

        except Exception as e:
            logger.error(
                f'Ошибка при обработке сообщения '
                f'{message.message_id}: {e}'
            )
            # Помечаем как ошибочное
            await self.redis.fail_message(message.message_id, str(e))
            await self._update_stats(last_error=str(e))

    async def _update_stats(
        self,
        last_poll_time: Optional[datetime] = None,
        last_error: Optional[str] = None
    ):
        """Обновить статистику.

        Args:
            last_poll_time: Время последнего опроса
            last_error: Последняя ошибка
        """
        stats = await self.redis.get_stats()
        stats.pending_messages = await self.redis.get_queue_length()
        stats.processing_messages = await self.redis.get_processing_count()
        stats.active_dialogs = await self.redis.get_active_dialogs_count()

        if last_poll_time:
            stats.last_poll_time = last_poll_time
        if last_error:
            stats.last_error = last_error

        await self.redis.save_stats(stats)


async def main():
    """Главная функция."""
    # Настройка логирования
    logger.remove()
    logger.add(
        sys.stderr,
        format=(
            '<green>{time:YYYY-MM-DD HH:mm:ss}</green> | '
            '<level>{level: <8}</level> | '
            '<cyan>{name}</cyan>:<cyan>{function}</cyan>:'
            '<cyan>{line}</cyan> - <level>{message}</level>'
        ),
        level='INFO'
    )

    # Создаем клиентов
    redis_url = getattr(settings, 'REDIS_URL', 'redis://redis:6379/0')
    redis_client = RedisClient(redis_url)
    await redis_client.connect()

    avito_client_id = getattr(settings, 'AVITO_CLIENT_ID', '')
    avito_client_secret = getattr(settings, 'AVITO_CLIENT_SECRET', '')
    avito_user_id = int(getattr(settings, 'AVITO_USER_ID', 0))

    if not avito_user_id:
        logger.error('AVITO_USER_ID не установлен в настройках')
        sys.exit(1)

    avito_client = AvitoAPIClient(
        client_id=avito_client_id,
        client_secret=avito_client_secret,
        user_id=avito_user_id
    )

    poll_interval = int(getattr(settings, 'AVITO_POLL_INTERVAL', 30))

    # Создаем worker
    worker = AvitoWorker(
        redis_client=redis_client,
        avito_client=avito_client,
        poll_interval=poll_interval
    )

    # Обработчик сигналов для graceful shutdown
    def signal_handler(signum, frame):
        logger.info('Получен сигнал завершения')
        asyncio.create_task(worker.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info('Worker остановлен пользователем')
    except Exception as e:
        logger.error(f'Критическая ошибка: {e}')
        sys.exit(1)
    finally:
        await redis_client.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
