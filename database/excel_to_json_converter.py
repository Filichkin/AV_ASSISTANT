#!/usr/bin/env python3
"""
Скрипт для конвертации Excel файла в JSON формат.
Читает данные из new_database.xlsx и сохраняет в JSON с указанными полями.
"""

import pandas as pd
import json
import os


def convert_excel_to_json(excel_file: str, output_file: str) -> None:
    """
    Конвертирует Excel файл в JSON с указанными полями.

    Args:
        excel_file: Путь к Excel файлу
        output_file: Путь к выходному JSON файлу
    """
    try:
        # Читаем Excel файл
        df = pd.read_excel(excel_file)

        # Создаем список для хранения конвертированных данных
        json_data = []

        # Проходим по каждой строке DataFrame
        for index, row in df.iterrows():
            # Создаем словарь с нужными полями, маппим русские названия колонок
            item = {
                'id': str(index + 1),  # ID начинается с 1
                'segment': str(row.get('сегмент', '')),
                'condition': str(row.get('состояние', '')),
                'processor': str(row.get('процессор', '')),
                'ram': str(row.get('оперативная память', '')),
                'ssd': str(row.get('SSD', '')),
                'video': str(row.get('видеокарта', '')),
                'diogonal': str(row.get('диагональ', '')),
                'text': str(row.iloc[9] if len(row) > 9 else ''),
                'url': str(row.get('ссылка на авито', ''))
            }

            json_data.append(item)

        # Сохраняем в JSON файл
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        print(f'Конвертация завершена. Данные сохранены в {output_file}')
        print(f'Обработано записей: {len(json_data)}')

    except FileNotFoundError:
        print(f'Ошибка: Файл {excel_file} не найден')
    except Exception as e:
        print(f'Ошибка при конвертации: {str(e)}')


def main():
    """Основная функция скрипта."""
    # Определяем пути к файлам
    current_dir = os.path.dirname(os.path.abspath(__file__))
    excel_file = os.path.join(current_dir, 'new_database.xlsx')
    output_file = os.path.join(current_dir, 'converted_data.json')

    # Проверяем существование Excel файла
    if not os.path.exists(excel_file):
        print(f'Файл {excel_file} не найден в текущей директории')
        return

    # Выполняем конвертацию
    convert_excel_to_json(excel_file, output_file)


if __name__ == '__main__':
    main()
