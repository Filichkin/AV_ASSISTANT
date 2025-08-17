# check=skip=SecretsUsedInArgOrEnv
ARG PYTHON_VERSION=3.12-slim

# ---------- deps: ставим билду-зависимости и собираем venv ----------
FROM python:${PYTHON_VERSION} AS deps
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app
# requirements агента лежат в agent/requirements.txt относительно корня проекта
COPY agent/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt


# ---------- runtime: тонкий слой + скопированный venv ----------
FROM python:${PYTHON_VERSION} AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app


# переносим собранный venv
COPY --from=deps /opt/venv /opt/venv

# кладём только исходники агента
WORKDIR /app
COPY agent /app/agent
COPY config.py /app/config.py

# если агенту понадобится что-то ещё из корня — добавь COPY соответствующих папок/файлов

# точка входа: python -m agent.app
ENTRYPOINT ["python", "-m", "agent.app"]