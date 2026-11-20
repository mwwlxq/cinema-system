from .DBcm import DBContextManager


def select_list(_sql, user_list):
    result = []

    with DBContextManager() as cursor:
        if cursor is None:
            raise ValueError("Не удалось получить курсор БД")

        cursor.execute(_sql, user_list)

        columns = [column[0] for column in cursor.description]

        for row in cursor.fetchall():
            result.append(dict(zip(columns, row)))

    return result