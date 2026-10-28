from database.DBcm import DBContextManager
from flask import current_app


def select_list(_sql, user_list: list) -> list | None:
    """
    Выполняет параметризованный SQL-запрос.
    :return: список кортежей (может быть пустым) или None, если при работе с БД произошла ошибка
    """
    result = None
    with DBContextManager(current_app.config['db_config']) as cursor:
        if cursor is None:  # курсор не создан
            raise ValueError('Курсор не создан')  # исключение обработает __exit__
        cursor.execute(_sql, user_list)
        result = cursor.fetchall()
    return result
