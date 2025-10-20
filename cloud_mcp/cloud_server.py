import asyncio
import signal
import sys
from typing import Dict, Any

from fastmcp import FastMCP
import httpx
from loguru import logger

from config import settings


mcp = FastMCP('avito_rag_agent')
mcp.settings.port = 8003
mcp.settings.host = '0.0.0.0'


_access_token: str | None = 'no token'
_access_token_lock = asyncio.Lock()


def _parse_retrieve_limit(value: str | None, default: int = 6) -> int:
    if value is None:
        return default
    try:
        limit = int(value)
        if limit <= 0:
            return default
        return limit
    except (TypeError, ValueError):
        return default


async def postprocess_retrieve_result(retrieve_result: Dict[str, Any]) -> str:
    result_str = 'Context:\n\n'
    results = retrieve_result.get('results', [])
    for idx, el in enumerate(results, start=1):
        content = el.get('content', '')
        metadata = el.get('metadata', {})
        result_str += (
            f'Document {idx}:\n'
            f'Content: {content}\n'
            f'Metadata: {metadata}\n\n'
        )
    return result_str


async def get_access_token() -> str:
    async with _access_token_lock:
        global _access_token
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                token_response = await client.post(
                    settings.AUTH_URL,
                    data={
                        'grant_type': 'client_credentials',
                        'client_id': settings.KEY_ID,
                        'client_secret': settings.KEY_SECRET,
                    },
                )
                token_response.raise_for_status()
                access_token = token_response.json().get('access_token')
                if not access_token:
                    raise ValueError(
                        'Ответ аутентификации не содержит access_token'
                        )
                _access_token = access_token
                return access_token
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f'Ошибка при получении access token. '
                f'Статус: {e.response.status_code}; '
                f'Сообщение: {e.response.text}'
            )
        except httpx.TimeoutException:
            raise RuntimeError('Таймаут при получении access token.')
        except httpx.RequestError as e:
            raise RuntimeError(f'Сетевая ошибка аутентификации: {e}')
        except Exception as e:
            raise RuntimeError(f'Неожиданная ошибка аутентификации: {e}')


@mcp.tool()
async def request_to_rag(query: str) -> str:
    """
    Инструмент обращается к API Базы Знаний и получает
    релевантные документы по запросу пользователя.
    На выходе выдает релевантные документы, которые нужно использовать
    для ответа на вопрос пользователя.
    Args:
        query: str - Запрос пользователя.
    Returns:
        Отформатированная строка с релевантными документами из базы знаний.
    Raises:
        ValueError: Ошибки связанные с некорректными параметрами.
        RuntimeError: Серверная ошибка.
    """
    retrieve_limit = _parse_retrieve_limit(
        settings.RETRIEVE_LIMIT,
        default=6
        )
    global _access_token

    async def do_rag_request(access_token: str):
        async with httpx.AsyncClient(timeout=20.0) as client:
            payload = {
                'project_id': settings.EVOLUTION_PROJECT_ID,
                'query': query,
                'retrieve_limit': retrieve_limit,
                'rag_version': settings.KNOWLEDGE_BASE_VERSION_ID,
            }
            return await client.post(
                settings.RETRIEVE_URL_TEMPLATE,
                json=payload,
                headers={'Authorization': f'Bearer {access_token}'},
            )

    if _access_token is None:
        await get_access_token()

    try:
        response = await do_rag_request(_access_token)
        if response.status_code == 401:
            # Токен истёк или неверен,
            # пробуем обновить токен и повторить попытку
            await get_access_token()  # обновит _access_token
            response = await do_rag_request(_access_token)
            if response.status_code == 401:
                # Второй 401 подряд = реальные проблемы.
                raise RuntimeError(
                    'Аутентификация не удалась: '
                    'повторный 401 при запросе к базе знаний.'
                )
        response.raise_for_status()
        retrieve_result = response.json()
    except httpx.HTTPStatusError as e:
        status = (
            e.response.status_code if e.response is not None else 'unknown'
            )
        message = (
            e.response.text if e.response is not None else 'no message'
            )
        raise RuntimeError(
            f'Не удалось получить релевантные документы. '
            f'Статус: {status}; Сообщение: {message}'
        )
    except httpx.TimeoutException:
        raise RuntimeError(
            'Не удалось получить релевантные документы. '
            'Таймаут запроса к Managed RAG'
        )
    except httpx.RequestError as e:
        raise RuntimeError(
            f'Не удалось получить релевантные документы. '
            f'Сетевая ошибка при запросе к Managed RAG: {e}'
        )
    except Exception as e:
        # Непредвиденная ошибка
        raise RuntimeError(
            f'Не удалось получить релевантные документы. '
            f'Неожиданная ошибка при запросе к Managed RAG: {e}'
        )

    postprocessed_retrieve_result = (
        await postprocess_retrieve_result(retrieve_result)
        )
    return postprocessed_retrieve_result


def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения."""
    logger.info('🛑 Получен сигнал завершения, останавливаем сервер...')
    sys.exit(0)


if __name__ == '__main__':
    logger.info('🌐 Запуск MCP Avito RAG Server...')
    logger.info(
        f'🚀 Сервер будет доступен на http://'
        f'{mcp.settings.host}:{mcp.settings.port}'
        )
    logger.info(
        f'📡 SSE endpoint: http://{mcp.settings.host}:{mcp.settings.port}/sse'
        )
    logger.info('✋ Для остановки нажмите Ctrl+C')

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        mcp.run(transport='sse')
    except KeyboardInterrupt:
        logger.info('🛑 Сервер остановлен пользователем')
    except Exception as e:
        logger.error(f'❌ Ошибка при запуске сервера: {e}')
        sys.exit(1)
