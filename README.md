# ИС «Кинотеатр» — Лабораторная работа №2. Авторизация внутренних пользователей

## Структура
```
app.py                     Главное меню (/), выход (/exit), регистрация blueprint
access.py                  декораторы login_required и group_required
data/db_config.json        параметры подключения к БД (app.config['db_config'])
data/db_access.json        словарь прав: группа -> разрешённые функции (app.config["db_access"])
data/cinema_users.sql      создание таблицы internal_user и тестовых пользователей
database/                  DBContextManager, select_list, SQLProvider
auth_bp/                   blueprint «Авторизация» (/auth/)
query_bp/                  blueprint «Работа с запросами» (/query/...)
templates/                 main_menu.html, exit.html, access_denied.html, message.html
static/style.css           оформление
```

## Тестовые пользователи
| Логин | Пароль | Группа |
|---|---|---|
| admin | admin | admin (администратор) |
| manager | manager | manager (менеджер) |
| cashier | cashier | cashier (кассир) |

## Запуск
```
pip install -r requirements.txt
# в DBeaver выполнить data/cinema_users.sql
python app.py        # http://127.0.0.1:5001
```
