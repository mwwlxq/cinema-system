from os import path

from flask import Blueprint, redirect, render_template, request, session, url_for

from auth_bp.model_route import model_route
from database.sql_provider import SQLProvider

blueprint_auth = Blueprint('auth_bp', __name__, template_folder='templates')
provider = SQLProvider(path.join(path.dirname(__file__), 'sql'))


@blueprint_auth.route('/', methods=['GET'])
def auth_index():
    return render_template('login.html', error_message='', login='')


@blueprint_auth.route('/', methods=['POST'])
def auth_result():
    user_info = model_route(provider, request.form)
    if user_info.status:
        session.clear()
        session['user_id'] = user_info.user_id
        session['user_login'] = user_info.login
        session['user_group'] = user_info.user_group
        return redirect(url_for('main_menu'))
    return render_template('login.html', error_message=user_info.error_message,
                           login=request.form.get('login', ''))
