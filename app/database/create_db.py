import time

import torch
import logging
from sqlalchemy import create_engine, Column, Integer, String, JSON
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pgvector.sqlalchemy import Vector
from langchain.embeddings import HuggingFaceEmbeddings

from your_data_module import SHOP_DATA  # список объектов
from app.config import get_db_url         # строка подключения к БД

logger = logging.getLogger(__name__)
Base = declarative_base()


class ProductEmbedding(Base):
    __tablename__ = 'product_embeddings'

    id = Column(Integer, primary_key=True)
    text = Column(String)
    metadata = Column(JSON)
    embedding = Column(Vector(384))  # размерность зависит от модели

def generate_pg_vector_db():
    try:
        start_time = time.time()

        logger.info("Подключение к PostgreSQL...")
        engine = create_engine(POSTGRES_URL)
        Session = sessionmaker(bind=engine)
        session = Session()

        logger.info("Создание таблицы (если не существует)...")
        Base.metadata.create_all(engine)

        logger.info("Загрузка модели эмбеддингов...")
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            model_kwargs={"device": "cuda" if torch.cuda.is_available() else "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        logger.info("Генерация эмбеддингов и загрузка в БД...")
        texts = [item["text"] for item in SHOP_DATA]
        vectors = embeddings.embed_documents(texts)

        for item, vector in zip(SHOP_DATA, vectors):
            record = ProductEmbedding(
                id=int(item["metadata"]["id"]),
                text=item["text"],
                metadata=item["metadata"],
                embedding=vector
            )
            session.merge(record)

        session.commit()
        logger.info(f"Успешно! Загрузка заняла {time.time() - start_time:.2f} сек")

    except Exception as e:
        logger.error(f"Ошибка при создании PG векторной БД: {e}")
        raise
