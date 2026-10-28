from os import path

from flask import Blueprint, render_template, request

from access import group_required, login_required
from database.sql_provider import SQLProvider
from query_bp.model_route import model_route

blueprint_query = Blueprint('query_bp', __name__, template_folder='templates')
provider = SQLProvider(path.join(path.dirname(__file__), 'sql'))

# Описание параметризованных запросов: все они выполняются по одной схеме
# (форма ввода -> проверка параметров -> SQL-запрос -> таблица с результатом)
QUERIES = {
    'schedule': {
        'title': 'Расписание сеансов на заданную дату',
        'endpoint': 'query_bp.schedule_by_date',
        'sql': 'schedule_by_date.sql',
        'headers': ['Фильм', 'Зал', 'Время'],
        'fields': [
            {'name': 'date', 'label': 'Дата', 'type': 'date'},
        ],
    },
    'tickets': {
        'title': 'Свободные билеты в диапазоне цен',
        'endpoint': 'query_bp.free_tickets_by_price',
        'sql': 'free_tickets_by_price.sql',
        'range': True,
        'headers': ['Фильм', 'Дата', 'Время', 'Ряд', 'Место', 'Цена'],
        'fields': [
            {'name': 'price_min', 'label': 'Цена от', 'type': 'number'},
            {'name': 'price_max', 'label': 'Цена до', 'type': 'number'},
        ],
    },
    'free': {
        'title': 'Количество свободных билетов на сеанс',
        'endpoint': 'query_bp.free_count_by_session',
        'sql': 'free_count_by_session.sql',
        'headers': ['Фильм', 'Дата', 'Время', 'Свободных билетов'],
        'fields': [
            {'name': 'session_id', 'label': 'Номер сеанса', 'type': 'number', 'integer': True},
        ],
    },
}


def process_query(query_name):
    """Общая схема всех запросов: GET - форма ввода, POST - проверка, запрос к БД и результат."""
    query = QUERIES[query_name]
    if request.method == 'GET':
        return render_template('input_param.html', query=query, values={})
    res_info = model_route(provider, request.form, query)
    if res_info.status:
        return render_template('dynamic.html', prod_title=query['title'],
                               headers=query['headers'], products=res_info.result)
    return render_template('input_param.html', query=query,
                           values=request.form, error_message=res_info.error_message)


@blueprint_query.route('/', methods=['GET'])
@login_required
@group_required
def query_menu():
    return render_template('query_menu.html', queries=QUERIES)


@blueprint_query.route('/schedule', methods=['GET', 'POST'])
@login_required
@group_required
def schedule_by_date():
    return process_query('schedule')


@blueprint_query.route('/tickets', methods=['GET', 'POST'])
@login_required
@group_required
def free_tickets_by_price():
    return process_query('tickets')


@blueprint_query.route('/free', methods=['GET', 'POST'])
@login_required
@group_required
def free_count_by_session():
    return process_query('free')
