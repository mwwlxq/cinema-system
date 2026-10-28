import json
from os import path

from flask import Flask, render_template, session

from access import has_access, login_required
from auth_bp.route import blueprint_auth
from query_bp.route import blueprint_query

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cinema-secret-key'

base_dir = path.dirname(__file__)
with open(path.join(base_dir, 'data', 'db_config.json'), encoding='utf-8') as f:  # параметры подключения к БД
    app.config['db_config'] = json.load(f)
with open(path.join(base_dir, 'data', 'db_access.json'), encoding='utf-8') as f:  # права групп пользователей
    app.config['db_access'] = json.load(f)

app.register_blueprint(blueprint_auth, url_prefix='/auth')
app.register_blueprint(blueprint_query, url_prefix='/query')

# функция доступна во всех шаблонах: позволяет не показывать пункты меню, недоступные группе
app.jinja_env.globals['has_access'] = lambda endpoint: has_access(session.get('user_group'), endpoint)
app.jinja_env.globals['group_names'] = {
    'admin': 'Администратор',
    'manager': 'Менеджер',
    'cashier': 'Кассир',
}


@app.route('/')
@login_required
def main_menu():
    return render_template('main_menu.html')


@app.route('/exit')
def exit_func():
    session.clear()  # завершение работы: удаляем данные пользователя из сессии
    return render_template('exit.html')


@app.errorhandler(404)
def page_not_found(_):
    return render_template('message.html', title='Страница не найдена',
                           message='Такой страницы нет в системе.'), 404


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=True)
