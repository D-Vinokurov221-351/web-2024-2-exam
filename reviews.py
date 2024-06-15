import io
from flask import render_template, request, redirect, url_for, flash, Blueprint, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from app import db
from check_user import CheckUser
from functools import wraps
import mysql.connector
import math

bp_review = Blueprint('review', __name__, url_prefix='/review')

PER_PAGE = 10

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('У вас недостаточно прав для доступа к данной странице.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@bp_review.route('/create/<int:index>', methods = ['POST', 'GET'])
@login_required
def create(index):
    uid = current_user.id
    if request.method == 'POST':
        mark = request.form.get('rating') # Оценка
        text = request.form.get('text') # Текст рецензии
        try:
            query = '''
                insert into Reviews (bid, uid, mark, text, status) values (%s, %s, %s, %s, '1')
            '''
            cursor = db.connection().cursor(named_tuple=True)
            cursor.execute(query, (index, uid, mark, text))
            db.connection().commit()
            cursor.close()
            return redirect(url_for('show_book', index=index))
        except mysql.connector.errors.DatabaseError:
            db.connection().rollback()
            flash(f'При создании Рецензии произошла ошибка.', 'danger')
            flash(f'({index}, {uid}, {mark}, {text})', 'danger')
            return render_template('reviews/create.html', book_id = index, user_id = uid)
    return render_template('reviews/create.html', book_id = index, user_id = uid)

@bp_review.route('/manage')
def manage():

    querry_count = '''SELECT COUNT(*) as cnt FROM Reviews WHERE status = '1' '''
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(querry_count)
    count = math.ceil((cursor.fetchone().cnt) / PER_PAGE)
    cursor.close()

    try:
        page = int(request.args.get('page', 1))
        query = '''
            select * FROM Reviews WHERE status = '1' LIMIT %s OFFSET %s;
            '''
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query, (PER_PAGE, PER_PAGE * (page - 1)))
        reviews = cursor.fetchall()
        cursor.close()
    except mysql.connector.errors.DatabaseError:
        db.connection().rollback()
        flash(f'При выгрузке рецензий произошла ошибка.', 'danger')
    return render_template('reviews/manage.html', reviews=reviews, page=page, count = count)

@bp_review.route('/accept')
def accept():
    return render_template('reviews/manage.html')


@bp_review.route('/reject')
def reject():
    return render_template('reviews/manage.html')
