# 💻 MCP Laptops Search  Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.0-green.svg)](https://github.com/jlowin/fastmcp)
[![Free API](https://img.shields.io/badge/API-Free-brightgreen.svg)](https://open-meteo.com/)

MCP сервер для получения данных о ноутбуках с использованием HuggingFaceEmbeddings и PGVector.

## 🚀 Возможности

- **🌍 Поиск ноутбуков по запросу и метаданным**
- **🌐 Мультиязычность** - поддержка любого языка
- **⚡ Быстро и надежно** - FastMCP 2.0 фреймворк

## 📦 Установка

```bash
# Клонируйте репозиторий
cd mcp_weather

# Установите зависимости
pip install -r requirements.txt

# Запустите сервер
python -m mcp_server.server_conn
```

## 🛠️ Доступные инструменты

### `search_products(query: str)`
Получает актуальную информацию о ноутбуках из базы данных.

```python
# Примеры использования
await search_products("Какой у вас самый лучший ноутбук Lenovo?")
await search_productsr("мне нужен ноутбук Apple до 50000") 
await search_products("хочу ноутбук от 30000 до 50000 рублей")
await search_products("I need laptop for ML till 80000")
```


## 🐳 Docker

```bash
# Сборка и запуск
docker-compose up --build

# Только сборка
docker build -t mcp-weather .

# Запуск контейнера
docker run -p 8001:8001 mcp-weather
```

## 🌐 Endpoints

- **SSE**: `http://localhost:8001/sse`
- **Messages**: `http://localhost:8001/messages/`


## 🏗️ Архитектура

- **FastMCP 2.0** - MCP фреймворк
- **httpx** - HTTP клиент
- **HuggingFaceEmbeddings и PGvector** - поиск информации в БД
- **pip** - управление зависимостями

## 📄 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

---

⭐ **Понравился проект? Поставьте звездочку!** ⭐ 