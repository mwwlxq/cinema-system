import json
from dataclasses import dataclass
from datetime import date

from database.select import select_list
from database.redis_provider import redis_client  # Импорт нашего клиента Redis


@dataclass
class ResultInfo:
    result: list
    status: bool
    error_message: str


def check_params(query: dict, user_input: dict) -> tuple[list, str]:

    params = []
    for field in query['fields']:
        value = user_input.get(field['name'], '').strip()
        if not value:
            return [], f'Не заполнено поле «{field["label"]}»'

        if field['type'] == 'date':
            try:
                value = date.fromisoformat(value)
            except ValueError:
                return [], f'Поле «{field["label"]}» должно быть датой'

        elif field['type'] == 'number':
            try:
                value = float(value)
            except ValueError:
                return [], f'Поле «{field["label"]}» должно быть числом'
            if value < 0:
                return [], f'Поле «{field["label"]}» не может быть отрицательным'
            if field.get('integer'):
                if not value.is_integer():
                    return [], f'Поле «{field["label"]}» должно быть целым числом'
                value = int(value)

        params.append(value)

    if query.get('range') and params[0] > params[1]:
        return [], 'Нижняя граница диапазона больше верхней'
    return params, ''


def model_route(provider, user_input: dict, query: dict) -> ResultInfo:
    # 1. Проверяем параметры (твой старый код)
    params, error_message = check_params(query, user_input)
    if error_message:
        return ResultInfo(result=[], status=False, error_message=error_message)

    # 2. Формируем уникальный ключ для кэша
    # Например: "schedule_by_date.sql:2026-05-11" или "free_tickets_by_price.sql:200.0_500.0"
    cache_key = f"{query['sql']}:{'_'.join(map(str, params))}"

    # 3. ПРОВЕРЯЕМ REDIS (есть ли данные в кэше?)
    try:
        cached_result = redis_client.get(cache_key)
        if cached_result:
            print(f"--- ВЗЯТО ИЗ КЭША REDIS: {cache_key} ---")
            # рпевращаем строку JSON обратно в список Python
            return ResultInfo(result=json.loads(cached_result), status=True, error_message='')
    except Exception as e:
        print(f"Ошибка Redis при чтении: {e}")

    # ЕСЛИ В КЭШЕ НЕТ - ИДЕМ В POSTGRESQL
    print(f"--- ЗАПРОС В POSTGRESQL: {cache_key} ---")
    _sql = provider.get(query['sql'])
    result = select_list(_sql, params)

    if result is None:
        return ResultInfo(result=[], status=False,
                          error_message='Ошибка при обращении к базе данных. Попробуйте позже')
    if not result:
        return ResultInfo(result=[], status=False,
                          error_message='По заданным параметрам данные не найдены')

    # сохраняем результат в redis на 5 мин(300 сек)
    try:
        # json.dumps превращает список кортежей в строку, которую можно сохранить в redis
        redis_client.setex(cache_key, 300, json.dumps(result, default=str))
    except Exception as e:
        print(f"Ошибка Redis при записи: {e}")

    return ResultInfo(result=result, status=True, error_message='')