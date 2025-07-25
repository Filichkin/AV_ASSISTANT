from datetime import datetime
from typing import Dict, Optional, Tuple
import httpx

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route, Mount

from loguru import logger
from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS
from mcp.server.sse import SseServerTransport

import torch
from sqlalchemy import create_engine, text

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.pgvector import PGVector

from config import get_db_url
from config import settings


# Создаем экземпляр MCP сервера с идентификатором "products"
mcp = FastMCP('products')


def connect_to_pgvector() -> PGVector:
    """Подключение к PostgreSQL (pgvector) как к векторному хранилищу."""
    try:
        logger.info('Проверка/создание расширения pgvector...')
        engine = create_engine(get_db_url())

        with engine.begin() as conn:
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))

        logger.info('Загрузка модели эмбеддингов...')
        embeddings = HuggingFaceEmbeddings(
            model_name=settings.LLM_MODEL_NAME,
            model_kwargs={
                'device': 'mps' if torch.backends.mps.is_available() else 'cpu'
                },
            encode_kwargs={'normalize_embeddings': True},
        )

        logger.info('Подключение к PGVector...')
        store = PGVector(
            connection_string=get_db_url(),
            collection_name=settings.COLLECTION_NAME,
            embedding_function=embeddings,
            use_jsonb=True,  # удобно хранить metadata в JSONB
        )

        logger.success('Успешное подключение к PostgreSQL/pgvector')
        return store

    except Exception as e:
        logger.error(f'Ошибка подключения к PostgreSQL/pgvector: {e}')
        raise


if __name__ == '__main__':
    connect_to_pgvector()
