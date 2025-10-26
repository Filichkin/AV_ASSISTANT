"""Модели данных для работы с очередью и состоянием диалогов."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MessageStatus(str, Enum):
    """Статус обработки сообщения."""

    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'


class AvitoMessage(BaseModel):
    """Модель сообщения из Avito."""

    message_id: str = Field(..., description='ID сообщения в Avito')
    chat_id: str = Field(..., description='ID чата в Avito')
    user_id: str = Field(..., description='ID пользователя')
    text: str = Field(..., description='Текст сообщения')
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description='Время создания сообщения'
    )
    status: MessageStatus = Field(
        default=MessageStatus.PENDING,
        description='Статус обработки'
    )
    retry_count: int = Field(
        default=0,
        description='Количество попыток обработки'
    )


class DialogState(BaseModel):
    """Состояние диалога с пользователем."""

    chat_id: str = Field(..., description='ID чата')
    user_id: str = Field(..., description='ID пользователя')
    last_message_id: Optional[str] = Field(
        None,
        description='ID последнего обработанного сообщения'
    )
    last_activity: datetime = Field(
        default_factory=datetime.utcnow,
        description='Время последней активности'
    )
    message_count: int = Field(
        default=0,
        description='Количество сообщений в диалоге'
    )


class WorkerStats(BaseModel):
    """Статистика работы воркера."""

    total_messages: int = Field(
        default=0,
        description='Всего обработано сообщений'
    )
    completed_messages: int = Field(
        default=0,
        description='Успешно обработано'
    )
    failed_messages: int = Field(
        default=0,
        description='Ошибок обработки'
    )
    active_dialogs: int = Field(
        default=0,
        description='Активных диалогов'
    )
    last_poll_time: Optional[datetime] = Field(
        None,
        description='Время последнего опроса Avito API'
    )
    last_error: Optional[str] = Field(
        None,
        description='Последняя ошибка'
    )
