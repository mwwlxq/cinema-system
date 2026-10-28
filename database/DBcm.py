# контекстный менеджер для работы с БД
import psycopg2
from psycopg2 import connect


class DBContextManager:
    def __init__(self, db_connect: dict):
        self.conn = None
        self.cursor = None
        self.db_connect = db_connect

    def __enter__(self):  # создаем соединение и курсор
        try:
            self.conn = connect(**self.db_connect)
            self.cursor = self.conn.cursor()
            return self.cursor
        except psycopg2.Error as err:  # ошибка подключения
            print(err.pgerror)
            return None  # вместо курсора возвращается None

    def __exit__(self, exc_type, exc_val, exc_tb):  # вызывается при выходе из with
        if exc_type:  # если были исключения, сообщаем о них
            print(exc_type)
            print(exc_val)
        if self.cursor:  # создан ли курсор
            if exc_type:
                self.conn.rollback()  # при исключении откатываемся
            else:
                self.conn.commit()  # иначе фиксируем изменения
            self.cursor.close()
            self.conn.close()
        return True  # исключение обработано, дальше не передается
