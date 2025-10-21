"""Клиент для работы с Avito Messenger API."""

from datetime import datetime
from typing import Dict, List, Optional

import httpx
from loguru import logger


class AvitoAPIClient:
    """Клиент для работы с Avito Messenger API."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        user_id: int,
        base_url: str = 'https://api.avito.ru'
    ):
        """Инициализация клиента Avito API.

        Args:
            client_id: Client ID для авторизации
            client_secret: Client Secret для авторизации
            user_id: ID пользователя (учетной записи) Avito
            base_url: Базовый URL API Avito
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_id = user_id
        self.base_url = base_url
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    async def _get_access_token(self) -> str:
        """Получить access token для API через client_credentials.

        Returns:
            Access token

        Raises:
            RuntimeError: При ошибке получения токена
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f'{self.base_url}/token',
                    data={
                        'grant_type': 'client_credentials',
                        'client_id': self.client_id,
                        'client_secret': self.client_secret,
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                token = data.get('access_token')
                if not token:
                    raise ValueError('Токен не найден в ответе')
                logger.info('Access token успешно получен')
                return token
        except httpx.HTTPStatusError as e:
            logger.error(
                f'Ошибка HTTP при получении токена: '
                f'{e.response.status_code}'
            )
            raise RuntimeError(f'Ошибка получения токена: {e}')
        except Exception as e:
            logger.error(f'Ошибка при получении токена: {e}')
            raise RuntimeError(f'Ошибка получения токена: {e}')

    async def _ensure_token(self):
        """Убедиться что токен актуален."""
        if self._access_token is None:
            self._access_token = await self._get_access_token()

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Выполнить запрос с автоматическим обновлением токена при 401.

        Args:
            method: HTTP метод (GET, POST и т.д.)
            url: URL для запроса
            **kwargs: Дополнительные параметры для httpx

        Returns:
            Response объект

        Raises:
            httpx.HTTPStatusError: При ошибке HTTP
        """
        await self._ensure_token()

        headers = kwargs.get('headers', {})
        headers['Authorization'] = f'Bearer {self._access_token}'
        kwargs['headers'] = headers

        async with httpx.AsyncClient() as client:
            response = await getattr(client, method.lower())(url, **kwargs)

            # Если токен истек, получаем новый и повторяем запрос
            if response.status_code == 401:
                logger.warning('Токен истек, получаем новый')
                self._access_token = await self._get_access_token()
                headers['Authorization'] = f'Bearer {self._access_token}'
                response = await getattr(client, method.lower())(url, **kwargs)

            response.raise_for_status()
            return response

    async def get_chats(
        self,
        unread_only: bool = False,
        item_ids: Optional[List[int]] = None,
        chat_types: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Получить список чатов.

        Args:
            unread_only: Только непрочитанные чаты
            item_ids: Фильтр по ID объявлений
            chat_types: Типы чатов (u2i, u2u)
            limit: Количество чатов (1-100)
            offset: Сдвиг для пагинации (0-1000)

        Returns:
            Список чатов

        Raises:
            RuntimeError: При ошибке запроса
        """
        try:
            params = {
                'unread_only': str(unread_only).lower(),
                'limit': limit,
                'offset': offset
            }

            if item_ids:
                params['item_ids'] = ','.join(map(str, item_ids))

            if chat_types:
                params['chat_types'] = ','.join(chat_types)

            response = await self._request_with_retry(
                'GET',
                f'{self.base_url}/messenger/v2/accounts/'
                f'{self.user_id}/chats',
                params=params,
                timeout=20.0
            )

            data = response.json()
            chats = data.get('chats', [])
            logger.info(f'Получено {len(chats)} чатов')
            return chats
        except httpx.HTTPStatusError as e:
            logger.error(
                f'Ошибка HTTP при получении чатов: '
                f'{e.response.status_code}'
            )
            raise RuntimeError(f'Ошибка получения чатов: {e}')
        except Exception as e:
            logger.error(f'Ошибка при получении чатов: {e}')
            raise RuntimeError(f'Ошибка получения чатов: {e}')

    async def get_chat_messages(
        self,
        chat_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Получить сообщения из чата (V3 API).

        Args:
            chat_id: ID чата
            limit: Количество сообщений (1-100)
            offset: Сдвиг для пагинации (0-1000)

        Returns:
            Список сообщений

        Raises:
            RuntimeError: При ошибке запроса
        """
        try:
            params = {
                'limit': limit,
                'offset': offset
            }

            response = await self._request_with_retry(
                'GET',
                f'{self.base_url}/messenger/v3/accounts/'
                f'{self.user_id}/chats/{chat_id}/messages/',
                params=params,
                timeout=20.0
            )

            messages = response.json()
            logger.info(
                f'Получено {len(messages)} сообщений из чата {chat_id}'
            )
            return messages
        except httpx.HTTPStatusError as e:
            logger.error(
                f'Ошибка HTTP при получении сообщений: '
                f'{e.response.status_code}'
            )
            raise RuntimeError(f'Ошибка получения сообщений: {e}')
        except Exception as e:
            logger.error(f'Ошибка при получении сообщений: {e}')
            raise RuntimeError(f'Ошибка получения сообщений: {e}')

    async def get_unread_chats(self) -> List[Dict]:
        """Получить все непрочитанные чаты.

        Returns:
            Список непрочитанных чатов

        Raises:
            RuntimeError: При ошибке запроса
        """
        return await self.get_chats(unread_only=True)

    async def send_message(
        self,
        chat_id: str,
        text: str
    ) -> Dict:
        """Отправить текстовое сообщение в чат (V1 API).

        Args:
            chat_id: ID чата
            text: Текст сообщения

        Returns:
            Данные отправленного сообщения

        Raises:
            RuntimeError: При ошибке отправки
        """
        try:
            payload = {
                'message': {
                    'text': text
                },
                'type': 'text'
            }

            response = await self._request_with_retry(
                'POST',
                f'{self.base_url}/messenger/v1/accounts/'
                f'{self.user_id}/chats/{chat_id}/messages',
                headers={'Content-Type': 'application/json'},
                json=payload,
                timeout=20.0
            )

            message_data = response.json()
            logger.info(f'Сообщение отправлено в чат {chat_id}')
            return message_data
        except httpx.HTTPStatusError as e:
            logger.error(
                f'Ошибка HTTP при отправке сообщения: '
                f'{e.response.status_code}'
            )
            raise RuntimeError(f'Ошибка отправки сообщения: {e}')
        except Exception as e:
            logger.error(f'Ошибка при отправке сообщения: {e}')
            raise RuntimeError(f'Ошибка отправки сообщения: {e}')

    async def mark_chat_as_read(self, chat_id: str) -> bool:
        """Отметить чат как прочитанный (V1 API).

        Args:
            chat_id: ID чата

        Returns:
            True если успешно
        """
        try:
            response = await self._request_with_retry(
                'POST',
                f'{self.base_url}/messenger/v1/accounts/'
                f'{self.user_id}/chats/{chat_id}/read',
                timeout=10.0
            )

            data = response.json()
            success = data.get('ok', False)
            if success:
                logger.info(f'Чат {chat_id} отмечен как прочитанный')
            return success
        except Exception as e:
            logger.warning(
                f'Не удалось отметить чат {chat_id} как прочитанный: {e}'
            )
            return False

    async def send_image_message(
        self,
        chat_id: str,
        image_id: str
    ) -> Dict:
        """Отправить сообщение с изображением (V1 API).

        Args:
            chat_id: ID чата
            image_id: ID загруженного изображения

        Returns:
            Данные отправленного сообщения

        Raises:
            RuntimeError: При ошибке отправки
        """
        try:
            payload = {
                'image_id': image_id
            }

            response = await self._request_with_retry(
                'POST',
                f'{self.base_url}/messenger/v1/accounts/'
                f'{self.user_id}/chats/{chat_id}/messages/image',
                headers={'Content-Type': 'application/json'},
                json=payload,
                timeout=20.0
            )

            message_data = response.json()
            logger.info(f'Изображение отправлено в чат {chat_id}')
            return message_data
        except httpx.HTTPStatusError as e:
            logger.error(
                f'Ошибка HTTP при отправке изображения: '
                f'{e.response.status_code}'
            )
            raise RuntimeError(f'Ошибка отправки изображения: {e}')
        except Exception as e:
            logger.error(f'Ошибка при отправке изображения: {e}')
            raise RuntimeError(f'Ошибка отправки изображения: {e}')

    async def upload_image(self, image_data: bytes) -> Dict[str, Dict]:
        """Загрузить изображение на сервер (V1 API).

        Args:
            image_data: Бинарные данные изображения

        Returns:
            Словарь с ID изображения и ссылками на разные размеры

        Raises:
            RuntimeError: При ошибке загрузки
        """
        try:
            files = {
                'uploadfile[]': ('image.jpg', image_data, 'image/jpeg')
            }

            response = await self._request_with_retry(
                'POST',
                f'{self.base_url}/messenger/v1/accounts/'
                f'{self.user_id}/uploadImages',
                files=files,
                timeout=30.0
            )

            images_data = response.json()
            logger.info('Изображение успешно загружено')
            return images_data
        except httpx.HTTPStatusError as e:
            logger.error(
                f'Ошибка HTTP при загрузке изображения: '
                f'{e.response.status_code}'
            )
            raise RuntimeError(f'Ошибка загрузки изображения: {e}')
        except Exception as e:
            logger.error(f'Ошибка при загрузке изображения: {e}')
            raise RuntimeError(f'Ошибка загрузки изображения: {e}')

    async def delete_message(
        self,
        chat_id: str,
        message_id: str
    ) -> bool:
        """Удалить сообщение (в течение 1 часа после отправки).

        Args:
            chat_id: ID чата
            message_id: ID сообщения

        Returns:
            True если успешно

        Raises:
            RuntimeError: При ошибке удаления
        """
        try:
            await self._request_with_retry(
                'POST',
                f'{self.base_url}/messenger/v1/accounts/'
                f'{self.user_id}/chats/{chat_id}/messages/{message_id}',
                timeout=10.0
            )

            logger.info(f'Сообщение {message_id} удалено из чата {chat_id}')
            return True
        except httpx.HTTPStatusError as e:
            logger.error(
                f'Ошибка HTTP при удалении сообщения: '
                f'{e.response.status_code}'
            )
            raise RuntimeError(f'Ошибка удаления сообщения: {e}')
        except Exception as e:
            logger.error(f'Ошибка при удалении сообщения: {e}')
            raise RuntimeError(f'Ошибка удаления сообщения: {e}')
