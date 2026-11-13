from database.DBcm import DBContextManager
from flask import current_app

def execute_transaction(queries_and_params: list) -> bool:
    with DBContextManager(current_app.config['db_config']) as cursor:
        if cursor is None:
            return False
        try:
            for sql, params in queries_and_params:
                cursor.execute(sql, params)
            return True
        except Exception as e:
            print(f"Ошибка транзакции: {e}")
            return False