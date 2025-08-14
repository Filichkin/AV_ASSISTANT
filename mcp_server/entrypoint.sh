#!/usr/bin/env bash
set -euo pipefail
[[ "${DEBUG:-0}" == "1" ]] && set -x

# ---- DB env ----
: "${DB_HOST:=pgvector}"
: "${DB_PORT:=5432}"
: "${DB_NAME:=appdb}"
: "${DB_USER:=appuser}"
: "${DB_PASSWORD:=apppassword}"

# имя коллекции (должно совпадать с settings.COLLECTION_NAME)
: "${COLLECTION_NAME:=product_embeddings}"

# разовая принудительная загрузка, игнорируя проверку (0/1)
: "${FORCE_LOAD:=0}"

# построим цельный URL, если его не передали
: "${DB_URL:=}"
: "${DATABASE_URL:=${DB_URL}}"
if [[ -z "${DATABASE_URL}" ]]; then
  export DATABASE_URL="postgresql+psycopg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
fi
echo "Using DATABASE_URL=$DATABASE_URL"

echo "Waiting for Postgres at ${DB_HOST}:${DB_PORT} ..."
until pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" >/dev/null 2>&1; do
  sleep 1
done
echo "Postgres is ready."

echo "Ensuring extension 'vector' exists..."
PGPASSWORD="${DB_PASSWORD}" psql "host=${DB_HOST} port=${DB_PORT} dbname=${DB_NAME} user=${DB_USER}" \
  -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS vector;"

NEED_LOAD=1
if [[ "${FORCE_LOAD}" != "1" ]]; then
  # есть ли таблица коллекций?
  TABLE_EXISTS=$(
    PGPASSWORD="${DB_PASSWORD}" psql "host=${DB_HOST} port=${DB_PORT} dbname=${DB_NAME} user=${DB_USER}" \
      -tA -c "SELECT 1 FROM information_schema.tables
              WHERE table_schema='public' AND table_name='langchain_pg_collection';"
  )
  if [[ "${TABLE_EXISTS}" == "1" ]]; then
    # есть ли запись именно с нужным именем коллекции?
    HAS_COLLECTION=$(
      PGPASSWORD="${DB_PASSWORD}" psql "host=${DB_HOST} port=${DB_PORT} dbname=${DB_NAME} user=${DB_USER}" \
        -tA -c "SELECT 1 FROM langchain_pg_collection
                WHERE name='${COLLECTION_NAME}' LIMIT 1;"
    )
    if [[ "${HAS_COLLECTION}" == "1" ]]; then
      echo "Collection '${COLLECTION_NAME}' already exists — skipping data load."
      NEED_LOAD=0
    fi
  fi
else
  echo "FORCE_LOAD=1 — will load data regardless of collection check."
fi

if [[ "${NEED_LOAD}" == "1" ]]; then
  echo "Loading data (cwd=/app/database) ..."
  cd /app/database
  ls -la .

  # Небуферизованный и подробный вывод, чтобы видеть ошибки
  python -X dev -u create_db.py
  echo "Data load finished."
fi

echo "Starting MCP server..."
cd /app
exec python -m mcp_server.server_conn