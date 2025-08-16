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

## 🚀 Использование

### Запуск агента

```bash
# Запуск основных сервисов
python -m agent.app

# Агент будет доступен на http://localhost:10002
```

### Запуск MCP сервера

```bash
# Запуск основных сервисов
python -m mcp_server.server_conn

# Агент будет доступен на http://localhost:10002
```


### Отправка сообщения (без потоковой передачи)
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