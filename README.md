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
# Основные настройки агента
AGENT_NAME=jira_mcp_agent
AGENT_DESCRIPTION="Jira MCP агент для управления проектами, задачами, спринтами и agile-процессами"
AGENT_VERSION=1.0.0

# Конфигурация модели
LLM_MODEL="evolution_inference/model-for-agent-space-test"
LLM_API_BASE="https://your-model-api-base-url/v1"

# MCP Configuration
MCP_URL=http://mcp-weather:8001/sse

# Phoenix мониторинг (опционально)
PHOENIX_PROJECT_NAME="ip_agent_adk"
PHOENIX_ENDPOINT="http://phoenix:6006/v1/traces"

# Серверные настройки
HOST="0.0.0.0"
PORT="10002"

# Мониторинг
ENABLE_PHOENIX="false"
ENABLE_MONITORING="true"
```