import json
from flask import current_app
from database.select import select_list
from database.DBcm import DBContextManager
from database.redis_provider import redis_client


def get_movies():
    """Получение списка фильмов с кэшированием в Redis"""
    cache_key = "movies_all"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            print(f"--- ВЗЯТО ИЗ КЭША REDIS: {cache_key} ---")
            return json.loads(cached)
    except Exception as e:
        print(f"Ошибка Redis при чтении: {e}")

    print(f"--- ЗАПРОС В POSTGRESQL: {cache_key} ---")
    result = select_list("SELECT id_movie, title FROM movie ORDER BY title", [])

    if result:
        try:
            redis_client.setex(cache_key, 300, json.dumps(result, default=str))
        except Exception as e:
            print(f"Ошибка Redis при записи: {e}")
    return result


def get_sessions(movie_id):
    """Получение сеансов (только будущих) с кэшированием"""
    cache_key = f"sessions_{movie_id}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            print(f"--- ВЗЯТО ИЗ КЭША REDIS: {cache_key} ---")
            return json.loads(cached)
    except Exception as e:
        print(f"Ошибка Redis при чтении: {e}")

    print(f"--- ЗАПРОС В POSTGRESQL: {cache_key} ---")
    # фильтруем прошедшие сеансы и сортируем по дате и времени
    sql = """
        SELECT id_session, date, time 
        FROM session 
        WHERE id_movie = %s
        ORDER BY date, time
    """
    result = select_list(sql, [movie_id])

    if result:
        try:
            redis_client.setex(cache_key, 300, json.dumps(result, default=str))
        except Exception as e:
            print(f"Ошибка Redis при записи: {e}")
    return result


def get_free_seats(provider, session_id):
    """Получение свободных мест с кэшированием"""
    cache_key = f"free_seats.sql:{session_id}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            print(f"--- ВЗЯТО ИЗ КЭША REDIS: {cache_key} ---")
            return json.loads(cached)
    except Exception as e:
        print(f"Ошибка Redis при чтении: {e}")

    print(f"--- ЗАПРОС В POSTGRESQL: {cache_key} ---")
    result = select_list(provider.get('free_seats.sql'), [session_id])

    if result:
        try:
            redis_client.setex(cache_key, 300, json.dumps(result, default=str))
        except Exception as e:
            print(f"Ошибка Redis при записи: {e}")
    return result


def checkout_cart(provider, cart: list, user_id: int) -> tuple[bool, str, int]:
    """
    Оформление заказа в одной транзакции.
    Возвращает: (Успех, Сообщение, Номер заказа)
    """
    tickets_to_buy = []
    total_price = 0.0

    # получаем id_ticket и считаем итоговую сумму
    for item in cart:
        res = select_list(provider.get('check_seat.sql'), [item['session_id'], item['row'], item['seat']])
        if not res:
            return False, f"Место {item['row']}-{item['seat']} уже продано или не существует!", 0

        id_ticket = res[0][0]
        price = float(res[0][1])
        total_price += price

        tickets_to_buy.append({
            'id_ticket': id_ticket,
            'session_id': item['session_id']
        })

    # выполняем всё в одной транзакции
    with DBContextManager(current_app.config['db_config']) as cursor:
        if cursor is None:
            return False, "Ошибка подключения к БД", 0

        try:
            # создаем заказ и получаем его ID
            cursor.execute(provider.get('create_order.sql'), [user_id, total_price])
            id_order = cursor.fetchone()[0]

            # продаем билеты и обновляем счетчики
            for t in tickets_to_buy:
                # Пытаемся продать. Условие AND is_sold = false защищает от двойной продажи
                cursor.execute(provider.get('sell_ticket.sql'), [id_order, t['id_ticket']])

                # проверяем, что обновилась ровно одна строка
                if cursor.rowcount != 1:
                    raise Exception("Место уже было куплено кем-то другим!")

                # увеличиваем sold_count для сеанса
                cursor.execute(provider.get('update_sold_count.sql'), [t['session_id']])

            # Если мы дошли сюда, значит всё успешно.
            # Контекстный менеджер (DBContextManager) автоматически сделает COMMIT при выходе из блока with.

        except Exception as e:
            print(f"Ошибка транзакции: {e}")
            # При исключении контекстный менеджер сделает ROLLBACK
            return False, "К сожалению, одно из мест уже купили. Заказ отменен, выберите другие места.", 0

    # 3. Сброс кэша (выполняется только если транзакция успешно прошла)
    try:
        for t in tickets_to_buy:
            redis_client.delete(f"free_seats.sql:{t['session_id']}")
            print(f"---  КЭШ REDIS ОЧИЩЕН ДЛЯ СЕАНСА: {t['session_id']} ---")
    except Exception as e:
        print(f"Ошибка Redis при очистке: {e}")

    return True, f"Заказ №{id_order} успешно оформлен! Сумма: {total_price} руб.", id_order