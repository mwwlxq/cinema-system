from database.select import select_list
from database.modify import execute_transaction
from database.redis_provider import redis_client
import json


def get_movies():
    cache_key = "movies_all"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    result = select_list("SELECT id_movie, title FROM movie", [])
    if result:
        redis_client.setex(cache_key, 300, json.dumps(result, default=str))
    return result


def get_sessions(movie_id):
    cache_key = f"sessions_{movie_id}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    # Убрали AND date >= CURRENT_DATE
    result = select_list("SELECT id_session, date, time FROM session WHERE id_movie = %s ORDER BY date, time", [movie_id])
    if result:
        redis_client.setex(cache_key, 300, json.dumps(result, default=str))
    return result


def get_free_seats(provider, session_id):
    cache_key = f"free_seats.sql:{session_id}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    result = select_list(provider.get('free_seats.sql'), [session_id])
    if result:
        redis_client.setex(cache_key, 300, json.dumps(result, default=str))
    return result


def checkout_cart(provider, cart: list, user_id: int) -> tuple[bool, str, int]:
    """Возвращает (Успех, Сообщение, Номер заказа)"""
    queries_to_execute = []
    total_price = 0.0

    # 1. Проверяем места и считаем сумму
    for item in cart:
        check_res = select_list(provider.get('check_seat.sql'), [item['session_id'], item['row'], item['seat']])
        if not check_res:
            return False, f"Место {item['row']}-{item['seat']} уже продано!", 0

        id_ticket = check_res[0][0]
        price = float(check_res[0][1])
        total_price += price
        item['id_ticket'] = id_ticket  # Запоминаем id для транзакции

    # 2. Выполняем транзакцию (сначала создаем заказ, потом обновляем билеты)
    try:
        from database.DBcm import DBContextManager
        from flask import current_app
        with DBContextManager(current_app.config['db_config']) as cursor:
            if not cursor:
                return False, "Ошибка подключения к БД", 0

            # Создаем заказ
            cursor.execute(provider.get('create_order.sql'), [user_id, total_price])
            id_order = cursor.fetchone()[0]

            # Продаем билеты
            for item in cart:
                cursor.execute(provider.get('sell_ticket.sql'), [item['id_ticket']])
                if cursor.rowcount == 0:
                    raise Exception("Место уже продано!")

                # Привязываем билет к заказу
                cursor.execute(provider.get('link_ticket_to_order.sql'), [id_order, item['id_ticket']])

                # Обновляем счетчик
                cursor.execute(provider.get('update_sold_count.sql'), [item['session_id']])

    except Exception as e:
        print(f"Ошибка транзакции: {e}")
        return False, "Ошибка при оформлении заказа (возможно, билет уже куплен).", 0

    # 3. Очистка кэша (безопасная)
    try:
        for item in cart:
            redis_client.delete(f"free_seats.sql:{item['session_id']}")
            print(f"--- 🗑️ КЭШ REDIS ОЧИЩЕН ДЛЯ СЕАНСА: {item['session_id']} ---")
    except Exception as e:
        print(f"Ошибка Redis при очистке: {e}")  # Заказ уже оформлен, не рушим его из-за Redis

    return True, f"Заказ №{id_order} успешно оформлен! Сумма: {total_price} руб.", id_order