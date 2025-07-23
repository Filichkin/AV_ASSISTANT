from mistralai import Mistral

from app.config import settings
from .manager import SharedAgentDialogManager


client = Mistral(settings.MISTRAL_TOKEN)

dialog = SharedAgentDialogManager(client)


reply1 = dialog.send('user1', 'Какой макбук посоветуешь?')
print('🤖:', reply1)

# Второй — с контекстом
reply2 = dialog.send('user2', 'Хочу купить металлоискатель')
print('🤖:', reply2)

reply3 = dialog.send(
    'user1', 'Подбери продавцов ближе к станции метро Маяковская'
    )
print('🤖:', reply3)

reply4 = dialog.send('user2', 'Какие лучшие модели для поска кладов?')
print('🤖:', reply4)
