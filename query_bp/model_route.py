from dataclasses import dataclass
from datetime import date

from database.select import select_list


@dataclass
class ResultInfo:
    result: list
    status: bool
    error_message: str


def check_params(query: dict, user_input: dict) -> tuple[list, str]:

    params = []
    for field in query['fields']:
        value = user_input.get(field['name'], '').strip()
        if not value:
            return [], f'Не заполнено поле «{field["label"]}»'

        if field['type'] == 'date':
            try:
                value = date.fromisoformat(value)
            except ValueError:
                return [], f'Поле «{field["label"]}» должно быть датой'

        elif field['type'] == 'number':
            try:
                value = float(value)
            except ValueError:
                return [], f'Поле «{field["label"]}» должно быть числом'
            if value < 0:
                return [], f'Поле «{field["label"]}» не может быть отрицательным'
            if field.get('integer'):
                if not value.is_integer():
                    return [], f'Поле «{field["label"]}» должно быть целым числом'
                value = int(value)

        params.append(value)

    if query.get('range') and params[0] > params[1]:
        return [], 'Нижняя граница диапазона больше верхней'
    return params, ''


def model_route(provider, user_input: dict, query: dict) -> ResultInfo:
    params, error_message = check_params(query, user_input)
    if error_message:
        return ResultInfo(result=[], status=False, error_message=error_message)

    _sql = provider.get(query['sql'])
    result = select_list(_sql, params)
    if result is None:
        return ResultInfo(result=[], status=False,
                          error_message='Ошибка при обращении к базе данных. Попробуйте позже')
    if not result:
        return ResultInfo(result=[], status=False,
                          error_message='По заданным параметрам данные не найдены')
    return ResultInfo(result=result, status=True, error_message='')
