# AI Agent Template

Современный шаблон для создания ИИ агентов на базе Google ADK (Agent Development Kit) с поддержкой MCP (Model Context Protocol) инструментов и Phoenix мониторинга.

## 🚀 Особенности

- **Google ADK Integration** - Использование передового SDK для разработки агентов
- **MCP Tools Support** - Интеграция с Model Context Protocol для расширяемых инструментов
- **LiteLLM** - Поддержка различных LLM моделей через единый интерфейс
- **Phoenix Monitoring** - Опциональный мониторинг и трейсинг выполнения
- **Docker Ready** - Полная контейнеризация с автоматической настройкой
- **A2A Protocol** - Agent-to-Agent коммуникация
- **CORS Support** - Готов для веб-интеграции
- **Flexible Configuration** - Настройка через переменные окружения

## 📁 Структура проекта

```
agent/
├── app/                     # Основной код приложения
│   ├── __main__.py         # Точка входа с Click CLI
│   ├── agent.py            # Класс AgentEvolution
│   └── agent_executor.py   # Исполнитель агента
```

## 🛠 Установка

### Быстрый старт с Docker (рекомендуется)

#### Оптимизированная сборка для мгновенного старта

Образ настроен для максимально быстрого запуска без синхронизации пакетов:

```bash
# Сборка оптимизированного образа
docker-compose build

# Запуск агента
docker-compose up -d
```

#### Ключевые оптимизации:

1. **Pre-installed dependencies** - все зависимости устанавливаются на этапе сборки
2. **Frozen lockfile** - используется `uv sync --frozen` для точного воспроизведения окружения
3. **Optimized layers** - правильный порядок COPY команд для максимального кеширования Docker слоев
4. **Direct Python execution** - запуск через `python -m app` вместо `uv run`


### Ручная установка

```bash
# Создание файла окружения
python -m venv venv
source venv/bin/activate

# Установка зависимостей (требуется pip)
pip install -r requirements.txt

# Настройка переменных окружения (см. раздел ниже)
nano .env

# Запуск агента
python -m agent.app
```

## ⚙️ Конфигурация

### Основные переменные окружения

```bash
# Основные настройки агента
AGENT_NAME=ai-agent-template
AGENT_DESCRIPTION=AI Agent на базе Google ADK и MCP tools
AGENT_VERSION=0.1.0

# Конфигурация модели
LLM_AGENT_MODEL=openai/gpt-oss-20b:free
LLM_API_BASE=https://openrouter.ai/api/v1

# MCP Tools
MCP_URL=http://0.0.0.0:8001/sse

# Серверные настройки
HOST=0.0.0.0
PORT=10002

# Phoenix мониторинг (опционально)
ENABLE_PHOENIX=true
PHOENIX_PROJECT_NAME=ai-agent-template
PHOENIX_ENDPOINT=http://localhost:6006/v1/traces

# Системный промпт
AGENT_SYSTEM_PROMPT=Вы - современный ИИ агент с расширенными возможностями. Используйте доступные инструменты для эффективного выполнения задач пользователя.

# Сообщение при обработке
PROCESSING_MESSAGE=🤖 Обрабатываю запрос...
```

### Пример минимальной конфигурации

```bash
AGENT_NAME=my-ai-agent
LLM_AGENT_MODEL=openai/gpt-oss-20b:free
LLM_API_BASE=https://openrouter.ai/api/v1
MCP_URL=http://0.0.0.0:8001/sse
```

## 🚀 Использование

### Через Docker

```bash
# Запуск основных сервисов
docker-compose up -d

# Агент будет доступен на http://localhost:10002
```


### Проверка состояния

```bash
# Статус всех контейнеров
docker compose ps

# Проверка здоровья
docker inspect --format='{{json .State.Health}}' a2a-agent | jq

# Просмотр логов
docker compose logs -f a2a-agent
```

## 🔧 Архитектура

### Основные компоненты

- **AgentEvolution** - Главный класс агента с LLM интеграцией
- **EvolutionAgentExecutor** - Исполнитель запросов агента
- **A2AStarletteApplication** - HTTP сервер на базе Starlette
- **MCPToolset** - Набор MCP инструментов
- **LiteLLM** - Абстракция для работы с различными LLM

### Поддерживаемые форматы

- **Входные данные**: `text`, `text/plain`
- **Выходные данные**: `text`, `text/plain`
- **Протоколы**: A2A (Agent-to-Agent), HTTP REST, SSE (Server-Sent Events)

## 📊 Мониторинг

### Phoenix Tracing

Для включения Phoenix мониторинга:

```bash
# Установить переменную окружения
ENABLE_PHOENIX=true

# Запустить с Phoenix
pip install arize-phoenix # установка
phoenix serve # запуск

# Phoenix Dashboard будет доступен на http://localhost:6006
```

### Логирование

Логи сохраняются в:
- Стандартный вывод (Docker logs)
- `agent_monitoring.log` (при простом мониторинге)


### Добавление новых инструментов

1. Настройте MCP сервер с нужными инструментами
2. Обновите `MCP_URL` в конфигурации
3. Инструменты автоматически подключатся через MCPToolset

### Кастомизация агента

Основная логика агента находится в `app/agent.py`. Вы можете:
- Изменить системный промпт
- Добавить дополнительные инструменты
- Настроить модель LLM
- Изменить логику обработки запросов

## 🐳 Docker команды

```bash
# Основные команды
docker compose build               # Сборка образов
docker compose up -d --build       # Если нужно пересобрать образы
docker compose up -d               # Запуск сервисов
docker stop $(docker ps -q)        # Остановка сервисов
docker compose restart             # Перезапуск
docker compose logs -f a2a-agent   # Просмотр логов

# Phoenix мониторинг
make phoenix                       # Запуск с мониторингом
make phoenix-down                  # Остановка Phoenix

# Утилиты
docker compose exec app bash       # Вход в контейнер агента
```

## 🌐 API Endpoints

- `GET /` - Информация об агенте (Agent Card)
- `POST /tasks` - Создание новой задачи
- `GET /tasks/{task_id}` - Получение статуса задачи
- `GET /tasks/{task_id}/stream` - SSE поток выполнения задачи

## 📋 Требования

- **Python**: 3.12+
- **Docker**: Для контейнеризации
- **pip**: Для управления зависимостями
- **MCP Server**: Для инструментов (опционально)

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для подробностей.

## 🔗 Полезные ссылки

- [Google ADK Documentation](https://developers.google.com/adk)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [LiteLLM Documentation](https://docs.litellm.ai/)
- [Phoenix Tracing](https://phoenix.arize.com/)


## 📦 Использование

### Запуск агента:

```bash
# Запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

### Проверка работы:

```bash
# Проверка статуса
curl http://localhost:10002/health

# Просмотр логов запуска
docker logs a2a-agent
```
