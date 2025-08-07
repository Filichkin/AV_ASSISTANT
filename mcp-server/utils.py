import re
from typing import Optional, Tuple


def extract_price_range(query: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Извлекает диапазон цен из запроса пользователя.

    Поддерживает:
    - "от 50000 до 70000"
    - "до 50000"
    - "от 70000"
    - "в пределах 30000–60000"
    - "цена до 100000"
    - "ценой от 30000"
    """
    # от X до Y
    match = re.search(r'от\s*(\d{4,7})\D+до\s*(\d{4,7})', query)
    if match:
        return int(match.group(1)), int(match.group(2))

    # до Y
    match = re.search(r'(до|не дороже|максимум|не более)\s*(\d{4,7})', query)
    if match:
        return None, int(match.group(2))

    # от X
    match = re.search(r'(от|цена от|начиная с|минимум)\s*(\d{4,7})', query)
    if match:
        return int(match.group(2)), None

    # диапазон X–Y
    match = re.search(r'(\d{4,7})\s*[-–]\s*(\d{4,7})', query)
    if match:
        return int(match.group(1)), int(match.group(2))

    return None, None
