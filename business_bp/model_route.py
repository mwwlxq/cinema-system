import json
from flask import current_app
from database.select import select_list
from database.DBcm import DBContextManager
from database.redis_provider import redis_client

CACHE_TTL = 300


def get_movies():
    cache_key = "business:movies:all"

    try:
        cached = redis_client.get(cache_key)
        if cached:
            print(f"ВЗЯТО ИЗ КЭША REDIS: {cache_key}")
            return json.loads(cached)
    except Exception as e:
        print(f"Ошибка Redis при чтении: {e}")

    print(f"ЗАПРОС В POSTGRESQL: {cache_key}")
    sql = "SELECT id_movie, title FROM movie ORDER BY title"
    result = select_list(sql, [])

    if result:
        try:
            redis_client.setex(
                cache_key,
                CACHE_TTL,
                json.dumps(result, ensure_ascii=False, default=str)
            )
        except Exception as e:
            print(f"Ошибка Redis при записи: {e}")

    return result


def get_sessions(movie_id):
    cache_key = f"business:sessions:{movie_id}"

    try:
        cached = redis_client.get(cache_key)
        if cached:
            print(f"ВЗЯТО ИЗ КЭША REDIS: {cache_key}")
            return json.loads(cached)
    except Exception as e:
        print(f"Ошибка Redis при чтении: {e}")

    print(f"ЗАПРОС В POSTGRESQL: {cache_key}")
    sql = "SELECT id_session, date, time FROM session WHERE id_movie = %s ORDER BY date, time"
    result = select_list(sql, [movie_id])

    if result:
        try:
            redis_client.setex(
                cache_key,
                CACHE_TTL,
                json.dumps(result, ensure_ascii=False, default=str)
            )
        except Exception as e:
            print(f"Ошибка Redis при записи: {e}")

    return result


def get_free_seats(provider, session_id):
    cache_key = f"business:free_seats:{session_id}"

    try:
        cached = redis_client.get(cache_key)
        if cached:
            print(f"ВЗЯТО ИЗ КЭША REDIS: {cache_key}")
            return json.loads(cached)
    except Exception as e:
        print(f"Ошибка Redis при чтении: {e}")

    print(f"ЗАПРОС В POSTGRESQL: {cache_key}")
    result = select_list(provider.get('free_seats.sql'), [session_id])

    if result:
        try:
            redis_client.setex(
                cache_key,
                CACHE_TTL,
                json.dumps(result, ensure_ascii=False, default=str)
            )
        except Exception as e:
            print(f"Ошибка Redis при записи: {e}")

    return result


def clear_ticket_cache(session_ids):
    try:
        for session_id in session_ids:
            cache_key = f"business:free_seats:{session_id}"
            redis_client.delete(cache_key)
            print(f"КЭШ СВОБОДНЫХ МЕСТ ОЧИЩЕН: {session_id}")

        pattern1 = "query:free_tickets_by_price.sql:*"
        keys1 = list(redis_client.scan_iter(match=pattern1))
        if keys1:
            redis_client.delete(*keys1)
        print("КЭШ free_tickets_by_price ОЧИЩЕН")

        pattern2 = "query:free_count_by_session.sql:*"
        keys2 = list(redis_client.scan_iter(match=pattern2))
        if keys2:
            redis_client.delete(*keys2)
        print("КЭШ free_count_by_session ОЧИЩЕН")

    except Exception as e:
        print(f"Ошибка Redis при очистке кэша: {e}")


def checkout_cart(provider, cart: list, user_id: int) -> tuple[bool, str, int]:
    tickets_to_buy = []
    total_price = 0.0

    for item in cart:
        res = select_list(
            provider.get('check_seat.sql'),
            [item['session_id'], item['row'], item['seat']]
        )

        if not res:
            return False, f"Место {item['row']}-{item['seat']} уже продано!", 0

        id_ticket = res[0]['id_ticket']
        price = float(res[0]['price'])
        total_price += price

        tickets_to_buy.append({
            'id_ticket': id_ticket,
            'session_id': item['session_id'],
            'row': item['row'],
            'seat': item['seat'],
            'price': price
        })

    id_order = 0

    try:
        with DBContextManager(current_app.config['db_config']) as cursor:
            if cursor is None:
                return False, "Ошибка подключения к БД", 0

            cursor.execute(
                provider.get('create_order.sql'),
                [user_id, total_price]
            )
            id_order = cursor.fetchone()[0]

            for ticket in tickets_to_buy:
                cursor.execute(
                    provider.get('sell_ticket.sql'),
                    [ticket['id_ticket']]
                )

                if cursor.rowcount != 1:
                    raise Exception("Место уже было куплено другим пользователем!")

                cursor.execute(
                    provider.get('create_order_item.sql'),
                    [id_order, ticket['session_id'], ticket['row'], ticket['seat'], ticket['price']]
                )
    except Exception as e:
        print(f"Ошибка транзакции: {e}")
        return False, "К сожалению, одно из мест уже купили. Заказ отменен.", 0

    session_ids = {ticket['session_id'] for ticket in tickets_to_buy}
    clear_ticket_cache(session_ids)

    return True, f"Заказ №{id_order} успешно оформлен! Сумма: {total_price} руб.", id_order