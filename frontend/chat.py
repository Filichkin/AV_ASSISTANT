import uuid

import gradio as gr
import requests

from config import settings
from .constants import GRAY_CSS, WELCOME_MESSAGE


def talk_to_agent(user_input, history):
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": user_input
                    }
                ],
                "messageId": str(uuid.uuid4()),
                "kind": "message"
            },
            "configuration": {
                "acceptedOutputModes": ["text/plain", "application/json"],
                "historyLength": 5,
                "blocking": True
            }
        }
    }

    try:
        response = requests.post(
            settings.AGENT_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        response_data = response.json()
        artifacts = response_data.get('result', {}).get('artifacts', [])
        if artifacts and artifacts[0].get('parts'):
            parts = artifacts[0]['parts']
            if parts[0].get('kind') == 'text':
                return parts[0].get('text', '[Нет текста в ответе]')
        return '[Ответ агента не содержит текст]'
    except Exception as e:
        return f'[Ошибка подключения к агенту: {str(e)}]'


gr.ChatInterface(
    fn=talk_to_agent,
    title='💬 Чат с А-ассистентом',
    theme='soft',
    chatbot=gr.Chatbot(
        value=WELCOME_MESSAGE.copy(),
        type='tuples',
        height=800
        ),
    css=GRAY_CSS
).launch(
    server_name='0.0.0.0',
    server_port=int(settings.FRONTEND_PORT)
)
