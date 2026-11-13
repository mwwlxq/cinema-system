from database.select import select_list
from database.modify import execute_transaction
from database.redis_provider import redis_client


def get_movies():
    return select_list("SELECT id_movie, title FROM movie", [])


def get_sessions(movie_id):
    return select_list("SELECT id_session, date, time FROM session WHERE id_movie = %s", [movie_id])


def get_free_seats(provider, session_id):
    return select_list(provider.get('free_seats.sql'), [session_id])


def checkout_cart(provider, cart: list) -> tuple[bool, str]:
    """Оформляет заказ. Возвращает (Успех?, Сообщение)."""
    queries_to_execute = []

    for item in cart:
        # Проверяем, не купил ли кто-то место, пока оно лежало в корзине
        check_res = select_list(provider.get('check_seat.sql'), [item['session_id'], item['row'], item['seat']])
        if not check_res:
            return False, f"Место {item['row']}-{item['seat']} уже продано!"

        id_ticket = check_res[0][0]

        # Подготавливаем транзакцию
        queries_to_execute.append((provider.get('sell_ticket.sql'), [id_ticket]))
        queries_to_execute.append((provider.get('update_sold_count.sql'), [item['session_id']]))

    # Выполняем всё одной транзакцией
    success = execute_transaction(queries_to_execute)

    if success:
        # СБРОС КЭША: удаляем старые данные о местах для этих сеансов
        for item in cart:
            redis_client.delete(f"free_seats.sql:{item['session_id']}")
        return True, "Заказ успешно оформлен!"
    else:
        return False, "Ошибка при оформлении заказа. Попробуйте позже."