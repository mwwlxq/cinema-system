select user_id, login, user_group
from internal_user
where login = %s and password = %s
