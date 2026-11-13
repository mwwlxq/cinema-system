from os import path
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from access import login_required, group_required
from database.sql_provider import SQLProvider
from business_bp.model_route import get_movies, get_sessions, get_free_seats, checkout_cart

blueprint_business = Blueprint('business_bp', __name__, template_folder='templates')
provider = SQLProvider(path.join(path.dirname(__file__), 'sql'))


@blueprint_business.route('/')
@login_required
@group_required
def index():
    movies = get_movies()
    return render_template('b_movie_list.html', movies=movies)


@blueprint_business.route('/sessions/<int:movie_id>')
@login_required
@group_required
def sessions(movie_id):
    sessions_list = get_sessions(movie_id)
    return render_template('b_session_list.html', sessions=sessions_list, movie_id=movie_id)


@blueprint_business.route('/seats/<int:session_id>')
@login_required
@group_required
def seats(session_id):
    seats_list = get_free_seats(provider, session_id)

    # Группируем места по рядам для удобного вывода: {1: [(1, 400), (2, 400)], 2: [...]}
    rows = {}
    for row, seat, price in seats_list:
        if row not in rows:
            rows[row] = []
        rows[row].append((seat, price))

    return render_template('b_hall_scheme.html', rows=rows, session_id=session_id)


@blueprint_business.route('/add_to_cart/<int:session_id>', methods=['POST'])
@login_required
@group_required
def add_to_cart(session_id):
    row = int(request.form.get('row'))
    seat = int(request.form.get('seat'))

    if 'cart' not in session:
        session['cart'] = []

    cart = session['cart']
    if not any(i['session_id'] == session_id and i['row'] == row and i['seat'] == seat for i in cart):
        cart.append({'session_id': session_id, 'row': row, 'seat': seat})
        session['cart'] = cart
        flash(f"Билет Ряд {row}, Место {seat} добавлен в корзину", "success")
    else:
        flash("Этот билет уже в корзине", "error")

    return redirect(url_for('business_bp.seats', session_id=session_id))


@blueprint_business.route('/cart')
@login_required
@group_required
def cart():
    return render_template('basket.html', cart=session.get('cart', []))


@blueprint_business.route('/checkout', methods=['POST'])
@login_required
@group_required
def checkout():
    cart = session.get('cart', [])
    if not cart:
        flash("Корзина пуста", "error")
        return redirect(url_for('business_bp.cart'))

    success, message = checkout_cart(provider, cart)

    if success:
        session.pop('cart', None)
        return render_template('b_success.html', message=message)
    else:
        flash(message, "error")
        return redirect(url_for('business_bp.cart'))