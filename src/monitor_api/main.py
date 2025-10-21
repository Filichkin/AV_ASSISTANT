"""FastAPI приложение для мониторинга работы Avito Worker."""

import sys
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from loguru import logger

from config import settings
from src.common.models import WorkerStats
from src.common.redis_client import RedisClient
from src.monitor_api.dashboard import get_dashboard_html


# Глобальный клиент Redis
redis_client: RedisClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # Startup
    global redis_client
    redis_url = getattr(settings, 'REDIS_URL', 'redis://redis:6379/0')
    redis_client = RedisClient(redis_url)
    await redis_client.connect()
    logger.info('Monitor API запущен')

    yield

    # Shutdown
    if redis_client:
        await redis_client.disconnect()
    logger.info('Monitor API остановлен')


app = FastAPI(
    title='Avito Worker Monitor API',
    description='API для мониторинга работы Avito Worker',
    version='1.0.0',
    lifespan=lifespan
)


@app.get('/')
async def root():
    """Главная страница с документацией."""
    return {
        'service': 'Avito Worker Monitor API',
        'version': '1.0.0',
        'endpoints': {
            '/health': 'Проверка здоровья сервиса',
            '/stats': 'Статистика работы воркера',
            '/queue': 'Информация об очереди сообщений',
            '/dialogs': 'Информация об активных диалогах',
            '/dashboard': 'Web-интерфейс с дашбордом',
        }
    }


@app.get('/health')
async def health_check() -> Dict[str, str]:
    """Проверка здоровья сервиса.

    Returns:
        Статус сервиса
    """
    try:
        # Проверяем подключение к Redis
        await redis_client.redis.ping()
        return {
            'status': 'healthy',
            'redis': 'connected'
        }
    except Exception as e:
        logger.error(f'Health check failed: {e}')
        raise HTTPException(status_code=503, detail=str(e))


@app.get('/stats', response_model=WorkerStats)
async def get_stats() -> WorkerStats:
    """Получить статистику работы воркера.

    Returns:
        Статистика воркера
    """
    try:
        stats = await redis_client.get_stats()
        return stats
    except Exception as e:
        logger.error(f'Ошибка при получении статистики: {e}')
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/queue')
async def get_queue_info() -> Dict[str, Any]:
    """Получить информацию об очереди сообщений.

    Returns:
        Информация об очереди
    """
    try:
        queue_length = await redis_client.get_queue_length()
        processing_count = await redis_client.get_processing_count()

        return {
            'queue_length': queue_length,
            'processing_count': processing_count,
            'total': queue_length + processing_count
        }
    except Exception as e:
        logger.error(f'Ошибка при получении информации об очереди: {e}')
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/dialogs')
async def get_dialogs_info() -> Dict[str, Any]:
    """Получить информацию об активных диалогах.

    Returns:
        Информация о диалогах
    """
    try:
        active_count = await redis_client.get_active_dialogs_count()

        return {
            'active_dialogs': active_count
        }
    except Exception as e:
        logger.error(f'Ошибка при получении информации о диалогах: {e}')
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/dashboard', response_class=HTMLResponse)
async def get_dashboard():
    """Web-интерфейс с дашбордом статистики.

    Returns:
        HTML страница с дашбордом
    """
    return get_dashboard_html()


if __name__ == '__main__':
    import uvicorn

    logger.remove()
    logger.add(
        sys.stderr,
        format=(
            '<green>{time:YYYY-MM-DD HH:mm:ss}</green> | '
            '<level>{level: <8}</level> | '
            '<cyan>{name}</cyan>:<cyan>{function}</cyan>:'
            '<cyan>{line}</cyan> - <level>{message}</level>'
        ),
        level='INFO'
    )

    port = int(getattr(settings, 'MONITOR_API_PORT', 8080))
    uvicorn.run(app, host='0.0.0.0', port=port)
