import json
import os

from mistralai import Mistral

from app.config import settings


class SharedAgentDialogManager:
    def __init__(self, client: Mistral):
        self.client = client
        self.agent_id = self._load_or_create_agent()
        self.user_conversations = {}  # user_id -> conversation_id

    def _load_or_create_agent(self) -> str:
        # Проверяем, есть ли сохранённый agent_id
        if os.path.exists(settings.AGENT_FILE):
            with open(settings.AGENT_FILE, 'r') as f:
                data = json.load(f)
                return data['agent_id']

        # Если нет — создаём нового агента
        agent = self.client.beta.agents.create(
            model=settings.MISTRAL_MODEL_NAME,
            name=settings.AGENT_NAME,
            description=settings.AGENT_DESCRIPTION,
            instructions=settings.AGENT_PROMPT
        )
        # Сохраняем agent_id в файл
        with open(settings.AGENT_FILE, 'w') as f:
            json.dump({"agent_id": agent.id}, f)

        print(f'Агент создан: agent_id = {agent.id}')
        return agent.id

    def send(self, user_id: str, message: str) -> str:
        conversation_id = self.user_conversations.get(user_id)

        if conversation_id is None:
            response = self.client.beta.conversations.start(
                agent_id=self.agent_id,
                inputs=[
                    {
                        "role": "user",
                        "content": message
                        }
                    ],
                store=True
            )
            self.user_conversations[user_id] = response.conversation_id
        else:
            response = self.client.beta.conversations.append(
                conversation_id=conversation_id,
                inputs=[
                    {
                        "role": "user",
                        "content": message
                        }
                    ]
            )

        return response.outputs[0].content

    def reset(self, user_id: str):
        if user_id in self.user_conversations:
            del self.user_conversations[user_id]
