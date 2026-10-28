from functools import wraps

from flask import current_app, redirect, render_template, request, session, url_for


def login_required(func):
    """Пропускает к функции только авторизованного пользователя."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' in session:  # пользователь прошел авторизацию
            return func(*args, **kwargs)
        return redirect(url_for('auth_bp.auth_index'))  # не авторизован - на форму входа
    return wrapper


def has_access(user_group: str, endpoint: str) -> bool:
    """Разрешена ли группе функция: в словаре может быть имя blueprint целиком или отдельной функции."""
    access = current_app.config['db_access']  # словарь: группа -> список разрешенных функций
    allowed = access.get(user_group, [])
    blueprint_name = endpoint.split('.')[0]
    return blueprint_name in allowed or endpoint in allowed


def group_required(func):
    """Пропускает к функции только группу, которой она разрешена в словаре db_access."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth_bp.auth_index'))
        if has_access(session.get('user_group'), request.endpoint):
            return func(*args, **kwargs)
        return render_template('access_denied.html'), 403
    return wrapper
