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

    cached_result = redis_client.get(cache_key)

    if cached_result is not None:

        return ResultInfo(
            result=json.loads(cached_result),
            status=True
        )

    # если результата в Redis нет,выполняем запрос к PostgreSQL

    sql = provider(query["sql"])

    result = select_list(
        sql,
        list(params.result.values())
    )

    # сохраняем результат в Redis

    redis_client.setex(
        cache_key,
        CACHE_TTL,
        json.dumps(
            result,
            ensure_ascii=False,
            default=str
        )
    )

    return ResultInfo(
        result=result,
        status=True
    )