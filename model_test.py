from litellm import completion

from config import settings

response = completion(
    model="mistral/mistral-tiny",
    messages=[{"role": "user", "content": "Привет, расскажи анекдот"}],
    api_key=settings.MISTRAL_TOKEN
)

print(response)
