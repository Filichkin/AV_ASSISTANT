"""Entry point для запуска Avito Worker через python -m."""

import asyncio

from src.avito_worker.worker import main

if __name__ == '__main__':
    asyncio.run(main())
