"""Entry point для запуска Monitor API через python -m."""

import sys

import uvicorn
from loguru import logger

from config import settings


if __name__ == '__main__':
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
    uvicorn.run(
        'src.monitor_api.main:app',
        host='0.0.0.0',
        port=port
    )
