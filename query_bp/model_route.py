import json
from dataclasses import dataclass

from database.select import select_list
from database.redis_provider import redis_client


CACHE_TTL = 300


@dataclass
class ResultInfo:
    result: list
    status: bool
    error_message: str = ""


def make_cache_key(query_name, params):
    """
    Формирует уникальный ключ Redis-кэша
    для конкретного запроса и его параметров.
    """

    normalized_params = json.dumps(
        params,
        sort_keys=True,
        ensure_ascii=False
    )

    return f"query:{query_name}:{normalized_params}"


def check_params(form_data, query):
    """
    Проверяет параметры формы.

    Возвращает ResultInfo, где result — dict с валидированными значениями
    в порядке следования полей из QUERIES[...]['fields'].
    """

    params = {}

    for field in query['fields']:
        name = field['name']
        label = field['label']
        value = form_data.get(name, '')
        value = value.strip() if isinstance(value, str) else ''

        if not value:
            return ResultInfo(
                result=[],
                status=False,
                error_message=f"Поле «{label}» обязательно для заполнения"
            )

        if field.get('integer'):
            try:
                value = int(value)
            except (TypeError, ValueError):
                return ResultInfo(
                    result=[],
                    status=False,
                    error_message=f"Поле «{label}» должно быть целым числом"
                )
        elif field.get('type') == 'number':
            try:
                value = float(value)
            except (TypeError, ValueError):
                return ResultInfo(
                    result=[],
                    status=False,
                    error_message=f"Поле «{label}» должно быть числом"
                )

        params[name] = value

    # Дополнительная проверка для запросов с диапазоном (price_min/price_max)
    if query.get('range') and 'price_min' in params and 'price_max' in params:
        if params['price_min'] > params['price_max']:
            return ResultInfo(
                result=[],
                status=False,
                error_message="Минимальная цена не может быть больше максимальной"
            )

    return ResultInfo(result=params, status=True)


def model_route(provider, form_data, query):
    """
    Проверяет параметры запроса, получает данные из Redis
    или PostgreSQL и сохраняет результат в Redis.
    """

    # Проверка параметров
    params = check_params(form_data, query)

    if not params.status:
        return params

    # формируем уникальный ключ кэша:
    # название SQL-запроса + его параметры
    cache_key = make_cache_key(
        query["sql"],
        params.result
    )

    # проверяем Redis
    try:
        cached_result = redis_client.get(cache_key)
    except Exception as e:
        print(f"Ошибка Redis при чтении: {e}")
        cached_result = None

    if cached_result is not None:
        return ResultInfo(
            result=json.loads(cached_result),
            status=True
        )

    # если результата в Redis нет, выполняем запрос к PostgreSQL
    sql = provider(query["sql"])

    result = select_list(
        sql,
        list(params.result.values())
    )

    # сохраняем результат в Redis
    try:
        redis_client.setex(
            cache_key,
            CACHE_TTL,
            json.dumps(result, ensure_ascii=False, default=str)
        )
    except Exception as e:
        print(f"Ошибка Redis при записи: {e}")

    return ResultInfo(
        result=result,
        status=True
    )