import asyncio

from fastmcp import Client


MCP_URL = 'http://localhost:8003/sse'


async def main():
    client = Client(MCP_URL)

    async with client:
        # Проверим, что клиент достучался
        tools = await client.list_tools()
        print('🔧 Доступные инструменты:', [tool.name for tool in tools])

        # Вызов без автогенерации аргументов из docstring
        result = await client.call_tool(
            'request_to_rag',
            arguments={
                'query': 'Найди самый дешевый ноутбук для работы'
                }
        )
        print('📄 Результат запроса:\n', result)


if __name__ == '__main__':
    asyncio.run(main())
