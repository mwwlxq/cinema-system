from dataclasses import dataclass

from database.select import select_list


@dataclass
class AuthInfo:
    user_id: int | None
    login: str
    user_group: str
    status: bool
    error_message: str


def model_route(provider, user_input: dict) -> AuthInfo:
    login = user_input.get('login', '').strip()
    password = user_input.get('password', '')
    if not login:
        return AuthInfo(None, '', '', False, 'Введите логин')
    if not password:
        return AuthInfo(None, '', '', False, 'Введите пароль')

    _sql = provider.get('user_by_login.sql')
    result = select_list(_sql, [login, password])
    if result is None:
        return AuthInfo(None, '', '', False, 'Ошибка при обращении к базе данных. Попробуйте позже')
    if not result:
        return AuthInfo(None, '', '', False, 'Неверный логин или пароль')
    user_id, user_login, user_group = result[0]
    return AuthInfo(user_id, user_login, user_group, True, '')
