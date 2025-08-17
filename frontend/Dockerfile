# check=skip=SecretsUsedInArgOrEnv
ARG PYTHON_VERSION=3.12-slim

# ---------- deps: собираем виртуальное окружение ----------
FROM python:${PYTHON_VERSION} AS deps
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY frontend/requirements.txt /app/requirements.txt
RUN python -m venv /opt/venv \
 && pip install --upgrade pip \
 && pip install -r /app/requirements.txt

# ---------- runtime: тонкий слой + скопанный venv ----------
FROM python:${PYTHON_VERSION} AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app

WORKDIR /app
COPY --from=deps /opt/venv /opt/venv
# кладём только исходники фронта
COPY frontend /app/frontend
COPY config.py /app/config.py

# запуск
ENTRYPOINT ["python", "-m", "frontend.chat"]