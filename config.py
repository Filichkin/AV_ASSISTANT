import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    DEFAULT_MIN_SIMILARITY: float = 0.50
    COLLECTION_NAME: str = 'product_embeddings'
    SHOP_DATA_URL: str = 'draft/app/database/shop_data_main.json'

    LLM_MODEL_NAME: str = (
        'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
        )
    LLM_AGENT_MODEL: str = 'openai/gpt-4'
    LLM_API_BASE: str = 'https://openrouter.ai/api/v1'
    OPENROUTER_API_KEY: str

    AGENT_FILE: str = 'agent_config.json'
    AGENT_NAME: str = 'Avito'
    AGENT_DESCRIPTION: str = 'Ассистент Авито'
    AGENT_PROMPT: str
    MCP_URL: str
    PROCESSING_MESSAGE: str = '📋 Обрабатываю ваш запрос...'
    HOST: str = '0.0.0.0'
    PORT: str = '10002'
    AGENT_ENDPOINT: str = 'http://127.0.0.1:10002'
    MAX_TOKENS: int = 1024

    DATABASE_PORT: int
    POSTGRES_PASSWORD: str
    POSTGRES_USER: str
    POSTGRES_DB: str
    POSTGRES_HOST: str

    model_config = SettingsConfigDict(
        env_file=os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '.env'
            )
    )


settings = Config()


def get_db_url():
    return (f'postgresql+psycopg2://{settings.POSTGRES_USER}:'
            f'{settings.POSTGRES_PASSWORD}@'
            f'{settings.POSTGRES_HOST}:{settings.DATABASE_PORT}/'
            f'{settings.POSTGRES_DB}'
            )
