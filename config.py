import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    DEFAULT_MIN_SIMILARITY: float = 0.3
    COLLECTION_NAME: str = 'product_embeddings'
    # для запуска в docker
    SHOP_DATA_URL: str = '/app/database/shop_data_main.json'
    # для локального запуска
    # SHOP_DATA_URL: str = 'shop_data_main.json'

    LLM_MODEL_NAME: str = (
        'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
        )
    # LLM_AGENT_MODEL: str = 'openai/gpt-4'
    LLM_AGENT_MODEL: str = 'openai/gpt-oss-20b:free'
    LLM_API_BASE: str = 'https://openrouter.ai/api/v1'
    OPENROUTER_API_KEY: str

    AGENT_VERSION: str = '1.0.0'
    AGENT_FILE: str = 'agent_config.json'
    AGENT_NAME: str = 'MarketBot Agent'
    AGENT_DESCRIPTION: str = 'MarketBot Agent'
    AGENT_PROMPT: str

    MCP_URL: str
    PROCESSING_MESSAGE: str = '📋 Обрабатываю ваш запрос...'
    HOST: str = '0.0.0.0'
    PORT: str = '10002'
    AGENT_ENDPOINT: str = 'http://127.0.0.1:10002'
    # AGENT_ENDPOINT: str = 'http://a2a-agent:10002' # для запуска в docker
    MAX_TOKENS: int = 1024
    APP_PORT: int = 8001

    POSTGRES_PORT: int
    POSTGRES_PASSWORD: str
    POSTGRES_USER: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    FORCE_LOAD: int = 0

    PGADMIN_EMAIL: str
    PGADMIN_PASSWORD: str
    PGADMIN_PORT: int = 5050

    FRONTEND_PORT: int = 10003
    ENABLE_PHOENIX: bool
    PHOENIX_ENDPOINT: str

    model_config = SettingsConfigDict(
        env_file=os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '.env'
            )
    )


settings = Config()


def get_db_url():
    return (f'postgresql+psycopg://{settings.POSTGRES_USER}:'
            f'{settings.POSTGRES_PASSWORD}@'
            f'{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/'
            f'{settings.POSTGRES_DB}'
            )
