import json
import time

from langchain_postgres.vectorstores import PGVector
from langchain_huggingface import HuggingFaceEmbeddings

from loguru import logger
from pgvector.sqlalchemy import Vector
from sqlalchemy import create_engine, Column, Integer, String, JSON, text
from sqlalchemy.ext.declarative import declarative_base
import torch

from config import get_db_url
from config import settings


Base = declarative_base()


class ProductEmbedding(Base):
    __tablename__ = 'product_embeddings'

    id = Column(Integer, primary_key=True)
    text = Column(String)
    meta = Column(JSON)
    embedding = Column(Vector(384))  # размерность зависит от модели


def connect_to_pgvector() -> PGVector:
    """Подключение к PostgreSQL (pgvector)
    как к векторному хранилищу через LangChain PGVector."""
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
            connection=get_db_url(),
            collection_name=settings.COLLECTION_NAME,
            embeddings=embeddings,
            use_jsonb=True,  # metadata будет храниться в JSONB
        )

        logger.success('Успешное подключение к PostgreSQL/pgvector')
        return store

    except Exception as e:
        logger.error(f'Ошибка подключения к PostgreSQL/pgvector: {e}')
        raise


def upload_pgvector_from_json(
    json_path: str = settings.SHOP_DATA_URL,
    clean_before: bool = False,
) -> None:
    """
    Загружает документы из JSON в коллекцию PGVector.

    Args:
        json_path: путь к JSON с объектами вида
            {
              "text": "...",
              "metadata": {..., "id": 123}
            }
        clean_before: если True — очищает коллекцию перед загрузкой
        (выполняется через прямой SQL по внутренним таблицам LangChain)
    """
    start = time.time()
    store = connect_to_pgvector()

    if clean_before:
        delete_pgvector_collection(settings.COLLECTION_NAME)

    logger.info('Чтение данных из JSON...')
    with open(json_path, 'r', encoding='utf-8') as f:
        shop_data = json.load(f)

    texts = [item['text'] for item in shop_data]
    metadatas = [item['metadata'] for item in shop_data]

    # (опционально) передаём ids,
    # чтобы потом можно было переиспользовать/чистить
    ids = [
        str(item['metadata'].get('id', i)) for i, item in enumerate(shop_data)
        ]

    logger.info(f'Генерация эмбеддингов и загрузка {len(texts)} документов...')
    store.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    logger.success(
        f'Загрузка заняла {time.time() - start:.2f} сек. '
        f'Коллекция: {settings.COLLECTION_NAME}'
    )


def delete_pgvector_collection(collection_name: str) -> None:
    """
    Полностью очищает коллекцию PGVector, созданную LangChain'ом.
    Делается через прямой SQL по внутренним таблицам LangChain:
      - langchain_pg_collection
      - langchain_pg_embedding
    """
    logger.warning(f'Очищаю коллекцию {collection_name}...')
    engine = create_engine(get_db_url())
    with engine.begin() as conn:
        # Удаляем embeddings для конкретной коллекции
        conn.execute(text("""
            DELETE FROM langchain_pg_embedding
            WHERE collection_id IN (
              SELECT id FROM langchain_pg_collection WHERE name = :name
            );
        """), {'name': collection_name})

        # Удаляем саму коллекцию
        conn.execute(text("""
            DELETE FROM langchain_pg_collection WHERE name = :name;
        """), {"name": collection_name})

    logger.success(f'Коллекция {collection_name} очищена.')


if __name__ == '__main__':
    upload_pgvector_from_json()
