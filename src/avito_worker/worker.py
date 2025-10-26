"""Главный worker для обработки сообщений из Avito."""

import asyncio
import signal
import sys
from datetime import datetime
from typing import Optional

from loguru import logger

from config import settings
from src.common.redis_client import RedisClient
from src.common.models import DialogState
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
            max_tokens=settings.MAX_TOKENS,
        )
        await self._agent_client.__aenter__()

        # Запускаем только цикл опроса (обработка сообщений происходит сразу)
        await self._poll_avito_loop()

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

                    # Получаем только последние сообщения из чата
                    messages = await self.avito.get_chat_messages(
                        chat_id=chat_id,
                        limit=5  # Получаем только последние 5 сообщений
                    )

                    # Фильтруем только входящие непрочитанные сообщения
                    unread_incoming_messages = []
                    for msg_data in messages:
                        # Проверяем направление (V3 API: 'in' или 'out')
                        direction = msg_data.get('direction')
                        if direction != 'in':
                            continue

                        # Проверяем статус прочтения (V3 API: is_read)
                        is_read = msg_data.get('is_read', False)
                        if is_read:
                            continue

                        # Извлекаем текст из content
                        content = msg_data.get('content', {})
                        if not isinstance(content, dict):
                            continue

                        text = content.get('text', '')
                        if not text:
                            # Пропускаем сообщения без текста
                            continue

                        unread_incoming_messages.append(msg_data)

                    # Обрабатываем только последнее непрочитанное сообщение
                    if unread_incoming_messages:
                        # API возвращает сообщения от СТАРЫХ к НОВЫМ
                        # Сортируем по возрастанию времени для гарантии
                        unread_incoming_messages.sort(
                            key=lambda x: x.get('created', 0)
                        )

                        # Берем последнее (самое новое) непрочитанное сообщение
                        last_message = unread_incoming_messages[-1]

                        # Сразу помечаем чат как прочитанный
                        await self.avito.mark_chat_as_read(chat_id)

                        # Обрабатываем сообщение сразу
                        await self._process_message_direct(
                            message_id=last_message['id'],
                            chat_id=chat_id,
                            user_id=str(last_message.get('author_id', '')),
                            text=last_message['content']['text']
                        )
                        total_messages += 1

                        logger.info(
                            f'Обработано последнее непрочитанное сообщение '
                            f'из {len(unread_incoming_messages)} доступных '
                            f'в чате {chat_id}'
                        )

                # Обновляем статистику
                await self._update_stats(
                    last_poll_time=datetime.utcnow()
                )

                if total_messages > 0:
                    logger.info(
                        f'Обработано {total_messages} '
                        f'сообщений из {len(unread_chats)} чатов'
                    )

            except asyncio.CancelledError:
                logger.info('Цикл опроса остановлен')
                break
            except Exception as e:
                logger.error(f'Ошибка при опросе Avito API: {e}')
                await self._update_stats(last_error=str(e))

            # Ждем перед следующим опросом
            try:
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                logger.info('Sleep прерван, завершаем цикл опроса')
                break

    async def _process_message_direct(
        self,
        message_id: str,
        chat_id: str,
        user_id: str,
        text: str
    ):
        """Обработать сообщение напрямую без очереди.

        Args:
            message_id: ID сообщения
            chat_id: ID чата
            user_id: ID пользователя
            text: Текст сообщения
        """
        try:
            logger.info(
                f'Обработка сообщения {message_id} '
                f'из чата {chat_id}'
            )

            # Обновляем состояние диалога
            dialog_state = await self.redis.get_dialog_state(chat_id)
            if not dialog_state:
                dialog_state = DialogState(
                    chat_id=chat_id,
                    user_id=user_id,
                )
            dialog_state.last_message_id = message_id
            dialog_state.last_activity = datetime.utcnow()
            dialog_state.message_count += 1
            await self.redis.save_dialog_state(dialog_state)

            # Получаем ответ от агента
            answer = await self._agent_client.get_answer(text)

            # Отправляем ответ в Avito
            await self.avito.send_message(
                chat_id=chat_id,
                text=answer
            )

            logger.info(
                f'Сообщение {message_id} '
                f'успешно обработано'
            )

            # Обновляем статистику (успешная обработка)
            await self._update_stats(
                increment_total=True,
                increment_completed=True
            )

        except Exception as e:
            logger.error(
                f'Ошибка при обработке сообщения '
                f'{message_id}: {e}'
            )
            # Обновляем статистику (ошибка)
            await self._update_stats(
                increment_total=True,
                increment_failed=True,
                last_error=str(e)
            )

    async def _update_stats(
        self,
        last_poll_time: Optional[datetime] = None,
        last_error: Optional[str] = None,
        increment_total: bool = False,
        increment_completed: bool = False,
        increment_failed: bool = False
    ):
        """Обновить статистику.

        Args:
            last_poll_time: Время последнего опроса
            last_error: Последняя ошибка
            increment_total: Увеличить счетчик всего сообщений
            increment_completed: Увеличить счетчик успешных
            increment_failed: Увеличить счетчик ошибок
        """
        stats = await self.redis.get_stats()
        stats.active_dialogs = await self.redis.get_active_dialogs_count()

        if increment_total:
            stats.total_messages += 1
        if increment_completed:
            stats.completed_messages += 1
        if increment_failed:
            stats.failed_messages += 1

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
    except asyncio.CancelledError:
        logger.info('Worker остановлен (cancelled)')
    except Exception as e:
        logger.error(f'Критическая ошибка: {e}')
        sys.exit(1)
    finally:
        try:
            await redis_client.disconnect()
        except asyncio.CancelledError:
            logger.debug(
                'Redis disconnect cancelled (это нормально при shutdown)'
            )
        except Exception as e:
            logger.error(f'Ошибка при отключении Redis: {e}')


if __name__ == '__main__':
    asyncio.run(main())
