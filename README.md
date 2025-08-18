# AI Agent Project with Google ADK, A2A Protocol and MCP Integration

Этот проект представляет собой реализацию AI агента с интеграцией Google ADK (Agent Development Kit), поддерживающего A2A (Agent-to-Agent) протокол для взаимодействия с другими агентами и расширяемого через MCP (Model Context Protocol) серверы. Проект включает в себя готовую инфраструктуру для разработки, тестирования и развертывания AI агентов с мониторингом и трейсингом.

## 🎯 Особенности

- **Google ADK Integration** - Использование передового SDK для разработки агентов
- **MCP Tools Support** - Интеграция с Model Context Protocol для расширяемых инструментов
- **LiteLLM** - Поддержка различных LLM моделей через единый интерфейс
- **Phoenix Monitoring** - Опциональный мониторинг и трейсинг выполнения
- **Docker Ready** - Полная контейнеризация с автоматической настройкой
- **A2A Protocol** - Agent-to-Agent коммуникация
- **Flexible Configuration** - Настройка через переменные окружения

## 📁 Структура проекта

```
av_assistant/
├── agent/                     # Директория агента
│   ├── app/                   # Основной код приложения
│   │   ├── __main__.py        # Точка входа с Click CLI
│   │   ├── agent.py           # Класс AgentEvolution
│   │   └── agent_executor.py  # Исполнитель агента
│   ├── Dockerfile             # Docker конфигурация
│   ├── requirements.txt       # Зависимости агента
│   └── README.md              # Документация агента
├──  database/                 # Утилиты базы-данных
│   ├── creata_db.py           # Основной скрипт созданиф базы-данных
|   ├── ragas.json             # Данные для RAGAS (опцилнально)
│   └── shop_data_main.json    # Пример заполнения базы-данных
├──  frontend/                 # Gradio веб-интерфейс для визуализации агента
│   ├── chat.py                # Основной чат с агентом
|   ├── requirements.txt       # Зависимости веб-интерфейса
|   ├── constants.py           # Стили и константы
│   └── Dockerfile             # Docker конфигурация
├── mcp_server/                # MCP сервер БД данных магазина
│   ├── server_conn.py         # Основной сервер
│   ├── Dockerfile             # Docker конфигурация
|   ├── requirements.txt       # Зависимости MCP сервера
|   ├── entrypoint.sh          # Сервисные скрипты для сборки
│   └── README.md              # Документация MCP сервера
├── config.py                  # Конфигурация проекта
├── docker-compose.yml         # Основная конфигурация Docker Compose
├── LICENSE                    # Лицензия проекта
├── README.md                  # Документация проекта
└── .gitignore                 # Игнорируемые файлы

```

## 🛠 Установка и быстрый старт

### Быстрый старт с Docker (рекомендуется)

```bash
# Сборка образов
docker-compose build

# Запуск основных сервисов
docker-compose up -d

# Агент будет доступен на http://localhost:10002
# MCP сервер будет доступен на http://localhost:8001
```

## 🚀 Использование

### Запуск агента (без Docker)

```bash
# Запуск основных сервисов
python -m agent.app

# Агент будет доступен на http://localhost:10002
```

### Запуск MCP сервера (без Docker)

```bash
# Запуск основных сервисов
python -m mcp_server.server_conn

# Создание векторной базы-данных из shop_data_main.json
python -m database.create_db

# Агент будет доступен на http://localhost:10002
```

### Запуск Gradio веб-интерфейса (без Docker)

```bash
# Запуск основных сервисов
python -m python -m frontend.chat

# Gradio будет доступен на http://0.0.0.0:10003
```


### Отправка сообщения (без потоковой передачи), опционально через Postman
```json
{
  "jsonrpc": "2.0",
  "id": "uuid",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "Мне нужен ноутбук Lenovo до 50000 рублей"
        }
      ],
      "messageId": "uuid",
      "kind": "message"
    },
    "configuration": {
      "acceptedOutputModes": ["text/plain", "application/json"],
      "historyLength": 5,
      "blocking": true
    }
  }
}
```


### Основные переменные окружения

В файле `.env` можно настроить следующие параметры:

```bash
# Основные настройки POSTGRES
POSTGRES_PORT=5432
POSTGRES_PASSWORD=12345
POSTGRES_USER=postgres
POSTGRES_DB=av_assistant
POSTGRES_HOST=localhost
POSTGRES_HOST=pgvector # для запуска в docker

# Основные настройки при создании базы-данных
LLM_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
COLLECTION_NAME=product_embeddings
FORCE_LOAD=0 # 1 - если необходимо создание БД при первой сборке в Docker

# Основные настройки PGADMIN
PGADMIN_EMAIL=admin@example.com
PGADMIN_PASSWORD=admin1234
PGADMIN_PORT=5050

# Основные настройки агента
AGENT_NAME=Avito
AGENT_VERSION=1.0.0
AGENT_PROMPT=Вы - профессиональный агент по получению информации о ноутбуках из базы данных

# Конфигурация модели агента
OPENROUTER_API_KEY=sk-or-v1
LLM_AGENT_MODEL=openai/gpt-oss-20b:free
LLM_API_BASE=https://openrouter.ai/api/v1

# MCP Configuration
MCP_URL=http://0.0.0.0:8001/sse 
APP_PORT=8001

# Phoenix мониторинг (опционально)
PHOENIX_ENDPOINT=http://localhost:6006/v1/traces
ENABLE_PHOENIX=True

# Серверные настройки
FRONTEND_PORT=10003
```

## 📋 Требования

- **Docker**: Для контейнеризации
- **MCP Server**: Для инструментов (опционально)

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для подробностей (если имеется).

## 🔗 Полезные ссылки

- [Google ADK Documentation](https://developers.google.com/adk)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [LiteLLM Documentation](https://docs.litellm.ai/)
- [Phoenix Tracing](https://phoenix.arize.com/)