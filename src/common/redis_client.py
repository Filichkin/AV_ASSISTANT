"""Клиент для работы с Redis."""

from typing import Optional

import redis.asyncio as aioredis
from loguru import logger

from .models import AvitoMessage, DialogState, MessageStatus, WorkerStats


class RedisClient:
    """Асинхронный клиент для работы с Redis."""

    # Ключи для Redis
    QUEUE_KEY = 'avito:messages:queue'
    PROCESSING_KEY = 'avito:messages:processing'
    DIALOG_PREFIX = 'avito:dialog:'
    STATS_KEY = 'avito:stats'
    MESSAGE_PREFIX = 'avito:message:'

    def __init__(self, redis_url: str):
        """Инициализация клиента Redis.

        Args:
            redis_url: URL для подключения к Redis
        """
        self._redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None

    async def connect(self):
        """Подключение к Redis."""
        self._redis = await aioredis.from_url(
            self._redis_url,
            encoding='utf-8',
            decode_responses=True
        )
        logger.info(f'Подключено к Redis: {self._redis_url}')

    async def disconnect(self):
        """Отключение от Redis."""
        if self._redis:
            await self._redis.close()
            logger.info('Отключено от Redis')

    @property
    def redis(self) -> aioredis.Redis:
        """Получить клиент Redis."""
        if self._redis is None:
            raise RuntimeError('Redis не подключен')
        return self._redis

    # ============= Работа с очередью сообщений =============

    async def enqueue_message(self, message: AvitoMessage) -> bool:
        """Добавить сообщение в очередь.

        Args:
            message: Сообщение для добавления

        Returns:
            True если сообщение добавлено успешно
        """
        try:
            # Сохраняем полную информацию о сообщении
            message_key = f'{self.MESSAGE_PREFIX}{message.message_id}'
            await self.redis.setex(
                message_key,
                3600,  # TTL 1 час
                message.model_dump_json()
            )
            # Добавляем ID в очередь
            await self.redis.rpush(self.QUEUE_KEY, message.message_id)
            logger.debug(f'Сообщение {message.message_id} добавлено в очередь')
            return True
        except Exception as e:
            logger.error(f'Ошибка при добавлении сообщения в очередь: {e}')
            return False

    async def dequeue_message(self) -> Optional[AvitoMessage]:
        """Извлечь сообщение из очереди для обработки.

        Returns:
            AvitoMessage или None если очередь пуста
        """
        try:
            # Атомарно перемещаем из очереди в обработку
            message_id = await self.redis.lmove(
                self.QUEUE_KEY,
                self.PROCESSING_KEY,
                'LEFT',
                'RIGHT'
            )
            if not message_id:
                return None

            # Получаем полную информацию о сообщении
            message_key = f'{self.MESSAGE_PREFIX}{message_id}'
            message_data = await self.redis.get(message_key)
            if not message_data:
                logger.warning(
                    f'Сообщение {message_id} не найдено в Redis'
                )
                # Удаляем из processing
                await self.redis.lrem(self.PROCESSING_KEY, 1, message_id)
                return None

            message = AvitoMessage.model_validate_json(message_data)
            message.status = MessageStatus.PROCESSING
            logger.debug(
                f'Сообщение {message.message_id} извлечено из очереди'
            )
            return message
        except Exception as e:
            logger.error(f'Ошибка при извлечении сообщения из очереди: {e}')
            return None

    async def complete_message(self, message_id: str) -> bool:
        """Отметить сообщение как обработанное.

        Args:
            message_id: ID сообщения

        Returns:
            True если успешно
        """
        try:
            # Удаляем из processing
            await self.redis.lrem(self.PROCESSING_KEY, 1, message_id)
            # Обновляем статус
            message_key = f'{self.MESSAGE_PREFIX}{message_id}'
            message_data = await self.redis.get(message_key)
            if message_data:
                message = AvitoMessage.model_validate_json(message_data)
                message.status = MessageStatus.COMPLETED
                await self.redis.setex(
                    message_key,
                    3600,
                    message.model_dump_json()
                )
            logger.debug(f'Сообщение {message_id} помечено как обработанное')
            return True
        except Exception as e:
            logger.error(f'Ошибка при завершении обработки сообщения: {e}')
            return False

    async def fail_message(self, message_id: str, error: str) -> bool:
        """Отметить сообщение как ошибочное.

        Args:
            message_id: ID сообщения
            error: Описание ошибки

        Returns:
            True если успешно
        """
        try:
            # Удаляем из processing
            await self.redis.lrem(self.PROCESSING_KEY, 1, message_id)
            # Обновляем статус
            message_key = f'{self.MESSAGE_PREFIX}{message_id}'
            message_data = await self.redis.get(message_key)
            if message_data:
                message = AvitoMessage.model_validate_json(message_data)
                message.status = MessageStatus.FAILED
                message.retry_count += 1
                await self.redis.setex(
                    message_key,
                    3600,
                    message.model_dump_json()
                )
            logger.error(
                f'Сообщение {message_id} помечено как ошибочное: {error}'
            )
            return True
        except Exception as e:
            logger.error(
                f'Ошибка при пометке сообщения как ошибочного: {e}'
            )
            return False

    async def get_queue_length(self) -> int:
        """Получить длину очереди сообщений."""
        return await self.redis.llen(self.QUEUE_KEY)

    async def get_processing_count(self) -> int:
        """Получить количество сообщений в обработке."""
        return await self.redis.llen(self.PROCESSING_KEY)

    # ============= Работа с состоянием диалогов =============

    async def save_dialog_state(self, state: DialogState) -> bool:
        """Сохранить состояние диалога.

        Args:
            state: Состояние диалога

        Returns:
            True если успешно
        """
        try:
            dialog_key = f'{self.DIALOG_PREFIX}{state.chat_id}'
            await self.redis.setex(
                dialog_key,
                86400,  # TTL 24 часа
                state.model_dump_json()
            )
            logger.debug(f'Состояние диалога {state.chat_id} сохранено')
            return True
        except Exception as e:
            logger.error(f'Ошибка при сохранении состояния диалога: {e}')
            return False

    async def get_dialog_state(
        self,
        chat_id: str
    ) -> Optional[DialogState]:
        """Получить состояние диалога.

        Args:
            chat_id: ID чата

        Returns:
            DialogState или None если не найдено
        """
        try:
            dialog_key = f'{self.DIALOG_PREFIX}{chat_id}'
            state_data = await self.redis.get(dialog_key)
            if not state_data:
                return None
            return DialogState.model_validate_json(state_data)
        except Exception as e:
            logger.error(f'Ошибка при получении состояния диалога: {e}')
            return None

    async def get_active_dialogs_count(self) -> int:
        """Получить количество активных диалогов."""
        try:
            keys = await self.redis.keys(f'{self.DIALOG_PREFIX}*')
            return len(keys)
        except Exception as e:
            logger.error(
                f'Ошибка при подсчете активных диалогов: {e}'
            )
            return 0

    # ============= Работа со статистикой =============

    async def save_stats(self, stats: WorkerStats) -> bool:
        """Сохранить статистику.

        Args:
            stats: Статистика воркера

        Returns:
            True если успешно
        """
        try:
            await self.redis.set(self.STATS_KEY, stats.model_dump_json())
            logger.debug('Статистика сохранена')
            return True
        except Exception as e:
            logger.error(f'Ошибка при сохранении статистики: {e}')
            return False

    async def get_stats(self) -> WorkerStats:
        """Получить статистику.

        Returns:
            WorkerStats с текущей статистикой
        """
        try:
            stats_data = await self.redis.get(self.STATS_KEY)
            if not stats_data:
                return WorkerStats()
            return WorkerStats.model_validate_json(stats_data)
        except Exception as e:
            logger.error(f'Ошибка при получении статистики: {e}')
            return WorkerStats()
