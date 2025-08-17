# check=skip=SecretsUsedInArgOrEnv
ARG PYTHON_VERSION=3.12-slim

# --------- deps stage: общие зависимости (одни и те же для agent и database)
FROM python:${PYTHON_VERSION} AS deps
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Изолируем зависимости в venv (удобно переиспользовать дальше)
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app
COPY mcp_server/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt


# --------- runtime stage: тонкий рантайм + уже собранный venv
FROM python:${PYTHON_VERSION} AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# libpq для работы psycopg на рантайме
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 postgresql-client \
 && rm -rf /var/lib/apt/lists/*

# Переносим готовые зависимости
COPY --from=deps /opt/venv /opt/venv

# Код приложения
WORKDIR /app
COPY mcp_server /app/mcp_server
COPY database   /app/database
COPY config.py /app/config.py

# скрипт точки входа
COPY mcp_server/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Чтобы можно было импортировать пакеты из корня проекта
ENV PYTHONPATH=/app

# Порт MCP-сервера
EXPOSE 8001

# Health check для мониторинга состояния сервера
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/sse/ || exit 1

# переменные окружения по умолчанию (могут быть переопределены в compose)
ENV DB_HOST=pgvector \
    DB_PORT=5432 \
    DB_NAME=appdb \
    DB_USER=appuser \
    DB_PASSWORD=apppassword 

# старт: ждём БД, опционально загружаем данные, запускаем сервер
ENTRYPOINT ["/entrypoint.sh"]
# если нужно напрямую — можно заменить на:
# CMD ["python", "-m", "mcp_server.server_conn"]