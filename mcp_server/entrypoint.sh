#!/usr/bin/env bash
set -euo pipefail
[[ "${DEBUG:-0}" == "1" ]] && set -x

echo "==== ENV at startup ===="
echo "POSTGRES_HOST=${POSTGRES_HOST:-<unset>}"
echo "POSTGRES_PORT=${POSTGRES_PORT:-<unset>}"
echo "POSTGRES_DB=${POSTGRES_DB:-<unset>}"
echo "POSTGRES_USER=${POSTGRES_USER:-<unset>}"
echo "POSTGRES_PASSWORD=<hidden>"
echo "COLLECTION_NAME=${COLLECTION_NAME:-<unset>}"
echo "FORCE_LOAD=${FORCE_LOAD:-<unset>}"
echo "INIT_DB=${INIT_DB:-<unset>} (compat)"
echo "========================"

# ---- Defaults ----
: "${POSTGRES_HOST:=pgvector}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_DB:=appdb}"
: "${POSTGRES_USER:=appuser}"
: "${POSTGRES_PASSWORD:=apppassword}"
: "${COLLECTION_NAME:=product_embeddings}"

# Back-compat: INIT_DB=1 трактуем как FORCE_LOAD=1, если FORCE_LOAD не задан
if [[ "${INIT_DB:-0}" == "1" && -z "${FORCE_LOAD:-}" ]]; then
  export FORCE_LOAD="1"
fi
: "${FORCE_LOAD:=0}"

# Построим цельный URL, если не передан
: "${DATABASE_URL:=}"
if [[ -z "${DATABASE_URL}" ]]; then
  export DATABASE_URL="postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
fi
echo "Using DATABASE_URL=${DATABASE_URL//:${POSTGRES_PASSWORD}@/:***@}"

# ---- Ждём сервер через системную БД 'postgres' ----
echo "Waiting for Postgres server at ${POSTGRES_HOST}:${POSTGRES_PORT} (user=${POSTGRES_USER}) ..."
ATTEMPTS=0
MAX_ATTEMPTS=90
until PGPASSWORD="${POSTGRES_PASSWORD}" psql \
         -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d postgres \
         -v ON_ERROR_STOP=1 -c "SELECT 1;" >/dev/null 2>&1; do
  ATTEMPTS=$((ATTEMPTS+1))
  if [ "${ATTEMPTS}" -ge "${MAX_ATTEMPTS}" ]; then
    echo "ERROR: Postgres is not reachable after ${MAX_ATTEMPTS}s."
    echo "pg_isready:"; pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" || true
    exit 1
  fi
  sleep 1
done
echo "Postgres server is up."

# ---- Убедиться, что целевая БД существует ----
EXISTS=$(
  PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d postgres -tA -c \
  "SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB}';"
)
if [[ "${EXISTS}" != "1" ]]; then
  echo "Creating database '${POSTGRES_DB}' ..."
  PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d postgres -v ON_ERROR_STOP=1 -c \
  "CREATE DATABASE ${POSTGRES_DB};"
fi
echo "Target database '${POSTGRES_DB}' is ready."

# ---- Расширение pgvector в целевой БД ----
echo "Ensuring extension 'vector' exists in '${POSTGRES_DB}'..."
PGPASSWORD="${POSTGRES_PASSWORD}" psql "host=${POSTGRES_HOST} port=${POSTGRES_PORT} dbname=${POSTGRES_DB} user=${POSTGRES_USER}" \
  -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS vector;"

# ---- Решаем, нужна ли загрузка данных ----
NEED_LOAD=1
if [[ "${FORCE_LOAD}" != "1" ]]; then
  TABLE_EXISTS=$(
    PGPASSWORD="${POSTGRES_PASSWORD}" psql "host=${POSTGRES_HOST} port=${POSTGRES_PORT} dbname=${POSTGRES_DB} user=${POSTGRES_USER}" -tA -c \
      "SELECT 1 FROM information_schema.tables
       WHERE table_schema='public' AND table_name='langchain_pg_collection';"
  )
  if [[ "${TABLE_EXISTS}" == "1" ]]; then
    HAS_COLLECTION=$(
      PGPASSWORD="${POSTGRES_PASSWORD}" psql "host=${POSTGRES_HOST} port=${POSTGRES_PORT} dbname=${POSTGRES_DB} user=${POSTGRES_USER}" -tA -c \
        "SELECT 1 FROM langchain_pg_collection
         WHERE name='${COLLECTION_NAME}' LIMIT 1;"
    )
    if [[ "${HAS_COLLECTION}" == "1" ]]; then
      echo "Collection '${COLLECTION_NAME}' already exists — skip loading."
      NEED_LOAD=0
    fi
  fi
else
  echo "FORCE_LOAD=1 — will load data regardless of collection check."
fi

# ---- Однократная загрузка данных ----
if [[ "${NEED_LOAD}" == "1" ]]; then
  echo "Loading data via /app/database/create_db.py (cwd=/app/database) ..."
  if [[ -f "/app/database/create_db.py" ]]; then
    cd /app/database
    ls -la .
    python -X dev -u create_db.py
    echo "Data load finished."
  else
    echo "WARNING: /app/database/create_db.py not found — skipping data load."
  fi
fi

# ---- Запуск MCP-сервера ----
echo "Starting MCP server..."
cd /app
exec python -m mcp_server.server_conn