# Avito Messenger Integration

Интеграция мессенджера Avito с RAG-агентом на основе GigaChat и MCP сервера.

## Архитектура

Система состоит из 4 независимых сервисов в Docker:

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Avito     │────▶│ Avito Worker │────▶│  MCP Server  │
│  Messenger  │     │              │     │  (RAG API)   │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │    Redis     │
                    │   (Queue)    │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Monitor API  │
                    │  (FastAPI)   │
                    └──────────────┘
```

### Компоненты

1. **Redis** - хранит очередь сообщений и состояние диалогов
2. **MCP Server** - существующий RAG сервер с базой знаний
3. **Avito Worker** - фоновый процесс для обработки сообщений:
   - Каждые 30 секунд опрашивает Avito API
   - Добавляет новые сообщения в Redis очередь
   - Извлекает сообщения из очереди
   - Отправляет в RAG-агент через MCP
   - Возвращает ответ в Avito
4. **Monitor API** - FastAPI для просмотра статистики

## Структура проекта

```
src/
├── common/                  # Общие модули
│   ├── __init__.py
│   ├── models.py           # Pydantic модели
│   └── redis_client.py     # Клиент для Redis
├── avito_worker/           # Avito Worker
│   ├── __init__.py
│   ├── avito_api.py        # Клиент Avito API
│   ├── agent_client.py     # Клиент RAG-агента
│   └── worker.py           # Главный процесс worker
├── monitor_api/            # Monitor API
│   ├── __init__.py
│   └── main.py            # FastAPI приложение
├── docker-compose.yml     # Docker Compose конфигурация
├── Dockerfile.mcp         # Dockerfile для MCP Server
├── Dockerfile.worker      # Dockerfile для Worker
├── Dockerfile.monitor     # Dockerfile для Monitor API
├── requirements.txt       # Python зависимости
├── .env.example          # Пример переменных окружения
└── README.md             # Документация
```

## Установка и запуск

### 1. Подготовка окружения

Скопируйте `.env.example` в корневую директорию проекта как `.env`:

```bash
cp src/.env.example ../.env
```

Заполните переменные окружения в `.env`:

```bash
# Avito API
AVITO_CLIENT_ID=your_client_id
AVITO_CLIENT_SECRET=your_client_secret

# GigaChat
GIGACHAT_CREDENTIALS=your_credentials
GIGACHAT_SCOPE=GIGACHAT_API_PERS

# Evolution AI (для MCP)
KEY_ID=your_key_id
KEY_SECRET=your_key_secret
EVOLUTION_PROJECT_ID=your_project_id
```

### 2. Запуск через Docker Compose

```bash
cd src/
docker-compose up -d
```

### 3. Проверка работы

Проверьте статус сервисов:

```bash
docker-compose ps
```

Откройте в браузере:
- Monitor Dashboard: http://localhost:8080/dashboard
- Monitor API docs: http://localhost:8080/docs
- Health check: http://localhost:8080/health

## API Monitor

### Endpoints

- `GET /` - Информация о сервисе
- `GET /health` - Проверка здоровья
- `GET /stats` - Статистика работы воркера
- `GET /queue` - Информация об очереди
- `GET /dialogs` - Активные диалоги
- `GET /dashboard` - Web-интерфейс с дашбордом

### Пример запроса статистики

```bash
curl http://localhost:8080/stats
```

Ответ:

```json
{
  "total_messages": 150,
  "pending_messages": 5,
  "processing_messages": 2,
  "completed_messages": 140,
  "failed_messages": 3,
  "active_dialogs": 12,
  "last_poll_time": "2025-10-21T10:30:00",
  "last_error": null
}
```

## Логирование

Просмотр логов сервисов:

```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f avito-worker
docker-compose logs -f mcp-server
docker-compose logs -f monitor-api
```

## Остановка

```bash
docker-compose down
```

Для удаления volumes с данными:

```bash
docker-compose down -v
```

## Масштабирование

Для увеличения производительности можно запустить несколько экземпляров worker:

```bash
docker-compose up -d --scale avito-worker=3
```

## Конфигурация

### Интервал опроса Avito API

По умолчанию: 30 секунд. Изменить в `.env`:

```bash
AVITO_POLL_INTERVAL=60  # опрос каждые 60 секунд
```

### Параметры Redis

Redis использует volume для сохранения данных между перезапусками.

### Параметры GigaChat

Температура генерации (0.0 - 1.0):

```bash
GIGACHAT_TEMPERATURE=0.7
```

## Troubleshooting

### Worker не получает сообщения

1. Проверьте credentials Avito API
2. Проверьте логи: `docker-compose logs -f avito-worker`
3. Проверьте подключение к Redis: `docker-compose logs -f redis`

### MCP Server недоступен

1. Проверьте health check: `curl http://localhost:8003/`
2. Проверьте credentials Evolution AI в `.env`
3. Проверьте логи: `docker-compose logs -f mcp-server`

### Monitor API показывает нулевую статистику

1. Проверьте что worker запущен и работает
2. Проверьте подключение к Redis
3. Дождитесь первого цикла опроса (30 секунд по умолчанию)

## Разработка

### Локальный запуск без Docker

```bash
# Установка зависимостей (из корневой директории проекта)
pip install -r src/requirements.txt
pip install -r agent/requirements.txt
pip install -r cloud_mcp/requirements.txt

# Запуск Redis
redis-server

# Запуск MCP Server (из корневой директории проекта)
python -m cloud_mcp

# Запуск Worker (из корневой директории проекта)
python -m src.avito_worker

# Запуск Monitor API (из корневой директории проекта)
python -m src.monitor_api
```

## Лицензия

MIT
