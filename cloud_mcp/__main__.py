"""Entry point для запуска MCP Server через python -m."""

import signal
import sys

from loguru import logger

from cloud_mcp.cloud_server import mcp


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
        f'📡 SSE endpoint: http://'
        f'{mcp.settings.host}:{mcp.settings.port}/sse'
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
