import asyncio
from typing import Any, Dict, List, Optional

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres.vectorstores import PGVector
from loguru import logger
from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS
from mcp.server.sse import SseServerTransport
from sqlalchemy import create_engine, text
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route, Mount
import torch
import uvicorn

from config import get_db_url, settings
from .utils import build_price_filter, extract_price_range


# Создаем экземпляр MCP сервера с идентификатором "products"
mcp = FastMCP('products')


class PGVectorSessionManager:
    _instance: Optional['PGVectorSessionManager'] = None
    _store: Optional[PGVector] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_store(self) -> PGVector:
        if self._store is None:
            logger.info('Проверка/создание расширения pgvector...')
            engine = create_engine(get_db_url())
            with engine.begin() as conn:
                conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))

            logger.info('Загрузка модели эмбеддингов...')
            embeddings = HuggingFaceEmbeddings(
                model_name=settings.LLM_MODEL_NAME,
                model_kwargs={
                    'device': 'mps' if torch.backends.mps.is_available()
                    else 'cpu'
                },
                encode_kwargs={'normalize_embeddings': True},
            )

            logger.info('Подключение к PGVector...')
            self._store = PGVector(
                connection=get_db_url(),
                collection_name=settings.COLLECTION_NAME,
                embeddings=embeddings,
                use_jsonb=True,
            )

            logger.success('Успешное подключение к PostgreSQL/pgvector')
        return self._store


def connect_to_pgvector() -> PGVector:
    """Подключение к PostgreSQL (pgvector) как к векторному хранилищу."""
    try:
        return PGVectorSessionManager().get_store()
    except Exception as e:
        logger.error(f'Ошибка подключения к PostgreSQL/pgvector: {e}')
        raise


async def async_connect_to_pgvector() -> PGVector:
    return await asyncio.to_thread(connect_to_pgvector)


def search_products(
    query: str,
    metadata_filter: Optional[Dict[str, Any]] = None,
    k: int = 3,
    min_similarity: float = settings.DEFAULT_MIN_SIMILARITY,
) -> List[Dict[Any, Any]]:
    """
    Поиск ноутбуков по запросу и (опционально)
    по метаданным в PostgreSQL/pgvector.

    Args:
        query (str): Текстовый запрос для поиска.
        metadata_filter (dict | None): Фильтр по метаданным
        (для PGVector при use_jsonb=True — равенство по ключам).
        k (int): Количество результатов.

    Returns:
        list[dict]: Найденные документы с метаданными и скором.
    """
    try:
        store = connect_to_pgvector()

        # В PGVector доступен similarity_search_with_score.
        # Параметр filter работает, если вы создавали
        # PGVector с use_jsonb=True.
        results = store.similarity_search_with_score(
            query,
            k=k,
            filter=metadata_filter
            )

        logger.info(f'Найдено {len(results)} результатов для запроса: {query}')
        logger.info(f'Результаты поиска: {results}')

        formatted_results = []
        for doc, score in results:
            if score < min_similarity:
                continue
            formatted_results.append(
                {
                    "text": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score
                }
            )
            logger.info(f'Найдено {formatted_results}')
        return formatted_results

    except Exception as e:
        logger.error(f'Ошибка при поиске в PGVector: {e}')
        raise


async def async_search_products(
    query: str,
    metadata_filter: Optional[Dict[str, Any]] = None,
    k: int = 3,
) -> List[Dict[str, Any]]:
    return await asyncio.to_thread(search_products, query, metadata_filter, k)


@mcp.tool()
async def get_searched_products(query: str) -> str:
    """
    Поиск ноутбуков по запросу и (опционально)
    по метаданным в PostgreSQL/pgvector.

    Args:
        query (str): Текстовый запрос для поиска.
        metadata_filter (dict | None): Фильтр по метаданным
        (для PGVector при use_jsonb=True — равенство по ключам).
        k (int): Количество результатов.

    Usage:
        get_searched_products('Какой у вас самый лучший ноутбук Lenovo?')
        get_searched_products('мне нужен ноутбук Apple до 50000')
        get_searched_products('хочу ноутбук от 30000 до 50000 рублей')
    """
    logger.info(f'Найдено: {query}')
    try:
        if not query:
            raise McpError(
                ErrorData(
                    code=INVALID_PARAMS,
                    message='Введите ваш поисковый запрос'
                )
            )
        min_price, max_price = extract_price_range(query)
        metadata_filter = build_price_filter(min_price, max_price)
        logger.info(f'Ценовой фильтр: {metadata_filter}')

        products_data = await async_search_products(
            query.strip(),
            metadata_filter=metadata_filter
            )
        if not products_data:
            return 'Ничего не найдено.'

        result_lines = []
        for product in products_data:
            description = product['text']
            price = product['metadata'].get('price')
            product_link = product['metadata'].get('product_link')
            result_lines.append(
                f'Товар: {description} Цена: {price} руб. '
                f'Ссылка на товар: {product_link}'
            )
        return '\n'.join(result_lines)

    except Exception as e:
        if isinstance(e, McpError):
            raise
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=f'Ошибка при получении данных о товарах: {str(e)}'
            )
        ) from e


# Настройка SSE транспорта
sse = SseServerTransport('/messages/')


async def handle_sse(request: Request):
    """Обработчик SSE соединений"""
    _server = mcp._mcp_server
    async with sse.connect_sse(
        request.scope,
        request.receive,
        request._send,
    ) as (reader, writer):
        await _server.run(
            reader,
            writer,
            _server.create_initialization_options()
        )


# Создание Starlette приложения
app = Starlette(
    debug=True,
    routes=[
        Route('/sse', endpoint=handle_sse),
        Mount('/messages/', app=sse.handle_post_message),
    ],
)

# if __name__ == '__main__':
#     for product in search_products(
#         query='какой у вас самый крутой пылесос?'
#     ):
#         print(product)


if __name__ == '__main__':
    print('Запуск MCP сервера поиска продуктов по запросу...')
    print('📡 Сервер будет доступен по адресу: http://localhost:8001')
    print('🔗 SSE endpoint: http://localhost:8001/sse')
    print('📧 Messages endpoint: http://localhost:8001/messages/')
    print('🛠️ Доступные инструменты:')
    print('   - get_searched_products(query) - поиск продуктов по запросу')

    uvicorn.run(app, host='0.0.0.0', port=8001)
