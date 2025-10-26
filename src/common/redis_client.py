"""Клиент для работы с Redis."""

from typing import Optional

import redis.asyncio as aioredis
from loguru import logger

from .models import DialogState, WorkerStats


class RedisClient:
    """Асинхронный клиент для работы с Redis."""

    # Ключи для Redis
    # QUEUE_KEY = 'avito:messages:queue'  # Deprecated: не используется
    # PROCESSING_KEY = 'avito:messages:processing'  # Deprecated
    # MESSAGE_PREFIX = 'avito:message:'  # Deprecated
    DIALOG_PREFIX = 'avito:dialog:'
    STATS_KEY = 'avito:stats'

    # TTL для DialogState (24 часа)
    DIALOG_TTL = 86400

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
    # DEPRECATED: Методы очереди больше не используются.
    # Сообщения обрабатываются напрямую в worker._process_message_direct
    # Оставлено для reference на случай будущего масштабирования
    #
    # Закомментированные методы:
    # - enqueue_message()
    # - dequeue_message()
    # - complete_message()
    # - fail_message()
    # - get_queue_length()
    # - get_processing_count()

    # ============= Работа с состоянием диалогов =============

    async def save_dialog_state(self, state: DialogState) -> bool:
        """Сохранить состояние диалога с автоматической очисткой.

        Args:
            state: Состояние диалога

        Returns:
            True если успешно

        Note:
            DialogState автоматически удаляется через 24 часа (DIALOG_TTL)
        """
        try:
            dialog_key = f'{self.DIALOG_PREFIX}{state.chat_id}'
            await self.redis.setex(
                dialog_key,
                self.DIALOG_TTL,
                state.model_dump_json()
            )
            logger.debug(
                f'Состояние диалога {state.chat_id} сохранено '
                f'(TTL: {self.DIALOG_TTL}s)'
            )
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
