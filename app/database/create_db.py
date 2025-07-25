import json
import time

from langchain_huggingface import HuggingFaceEmbeddings
from loguru import logger
from sqlalchemy import create_engine, Column, Integer, String, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pgvector.sqlalchemy import Vector
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


def generate_pg_vector_db():
    try:
        start_time = time.time()

        logger.info('Подключение к PostgreSQL...')
        engine = create_engine(get_db_url())
        Session = sessionmaker(bind=engine)
        session = Session()

        logger.info('Создание таблицы (если не существует)...')
        Base.metadata.create_all(engine)

        logger.info('Загрузка модели эмбеддингов...')
        embeddings = HuggingFaceEmbeddings(
            model_name=settings.LLM_MODEL_NAME,
            model_kwargs={
                'device': 'mps' if torch.backends.mps.is_available() else 'cpu'
                },
            encode_kwargs={'normalize_embeddings': True},
        )

        logger.info('Генерация эмбеддингов и загрузка в БД...')
        with open(settings.SHOP_DATA_URL, 'r', encoding='utf-8') as f:
            SHOP_DATA = json.load(f)

        texts = [item['text'] for item in SHOP_DATA]
        vectors = embeddings.embed_documents(texts)

        for item, vector in zip(SHOP_DATA, vectors):
            record = ProductEmbedding(
                id=int(item['metadata']['id']),
                text=item['text'],
                meta=item['metadata'],
                embedding=vector
            )
            session.merge(record)

        session.commit()
        logger.info(
            f'Успешно! Загрузка заняла {time.time() - start_time:.2f} сек')

    except Exception as e:
        logger.error(f'Ошибка при создании PG векторной БД: {e}')
        raise


if __name__ == '__main__':
    generate_pg_vector_db()
