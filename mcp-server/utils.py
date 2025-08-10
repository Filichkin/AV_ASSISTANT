import re
from typing import Optional, Tuple


RE_NUM = (
    r'(\d{1,3}(?:[ \u00A0]?\d{3})+|\d+)'
    r'(?:\s*(?:₽|р(?:уб)?\.?|руб(?:\.|лей|ля)?))?'
    )


def _to_int(s: str) -> int:
    """
    Преобразует строку с ценой в число.
    Поддерживает: '50k', '50 k', '50 000', '50 тыс', '50 тысяч'
    """
    s = s.lower().strip()
    # заменяем 'k', 'тыс', 'тысяч' на '000'
    s = re.sub(r'(k|тыс(?:яч)?)\b', '000', s)
    # убираем всё, кроме цифр
    digits = re.sub(r'\D', '', s)
    return int(digits) if digits else 0


def extract_price_range(query: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Поддерживает:
    - 'от 50000 до 70000', 'между 50000 и 70000'
    - '50000 до 70000'  ← новый кейс (без 'от')
    - '50000–70000' / '50000-70000'
    - 'до 100000', 'не дороже 100000', '<= 100000'
    - 'от 70000', 'дороже 70000', '>= 70000'
    - любые скобки: '(50000 до 70000)'
    """
    q = query.lower()
    q = re.sub(r'[()]+', ' ', q)   # убираем скобки
    q = re.sub(r'\s+', ' ', q).strip()

    # от X до Y
    m = re.search(rf'от\s*{RE_NUM}\s*(?:до|по)\s*{RE_NUM}', q)
    if m:
        return _to_int(m.group(1)), _to_int(m.group(2))

    # X до Y   ← БЕЗ 'от'
    m = re.search(rf'{RE_NUM}\s*(?:до|по)\s*{RE_NUM}', q)
    if m:
        return _to_int(m.group(1)), _to_int(m.group(2))

    # между X и Y
    m = re.search(rf'между\s*{RE_NUM}\s*и\s*{RE_NUM}', q)
    if m:
        return _to_int(m.group(1)), _to_int(m.group(2))

    # X–Y
    m = re.search(rf'{RE_NUM}\s*[-–—]\s*{RE_NUM}', q)
    if m:
        return _to_int(m.group(1)), _to_int(m.group(2))

    # до Y
    m = re.search(rf'(?:до|не\s*дороже|<=|<)\s*{RE_NUM}', q)
    if m:
        return None, _to_int(m.group(1))

    # от/дороже X
    m = re.search(rf'(?:от|не\s*дешевле|дороже|>=|>)\s*{RE_NUM}', q)
    if m:
        return _to_int(m.group(1)), None

    return None, None


def build_price_filter(min_price: int | None, max_price: int | None):
    if min_price is not None and max_price is not None:
        # оба края — объединяем логически
        return {"$and": [
            {"price": {"$gte": min_price}},
            {"price": {"$lte": max_price}},
        ]}
    if min_price is not None:
        return {"price": {"$gte": min_price}}
    if max_price is not None:
        return {"price": {"$lte": max_price}}
    return None
