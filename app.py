from flask import Flask, render_template, request, redirect, url_for, flash, send_file, send_from_directory
from flask_login import login_required, current_user
from mysql_db import MySQL
import mysql.connector
from typing import Dict
import re
import math
import markdown

app = Flask(__name__)

application = app

app.config.from_pyfile('config.py')

db = MySQL(app)

from auth import bp_auth, check_rights, init_login_manager
from reviews import bp_review
from admin import bp_admin

app.register_blueprint(bp_auth)
app.register_blueprint(bp_review)
app.register_blueprint(bp_admin)

init_login_manager(app)

PER_PAGE = 10

@app.route('/get_image', methods=['GET'])
def get_image():
    md5 = request.args.get('md5')
    mime = request.args.get('mime')
    filename = f"{md5}.{mime.split('/')[1]}"
    return send_from_directory('images', filename)

@app.route('/')
def index():
    querry_count = '''SELECT COUNT(*) as cnt FROM Books'''
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(querry_count)
    count = math.ceil((cursor.fetchone().cnt) / PER_PAGE)
    cursor.close()

    querry_data = '''
    SELECT Books.name as name, Books.year as year, Skins.mime as mime, Skins.md5 as md5, GROUP_CONCAT(Genres.name) as genres,  
    AVG(IFNULL(Reviews.mark, 0)) as mark, count(Reviews.id) as reviews, Books.id as id FROM Books 
    LEFT JOIN Skins ON Books.skin = Skins.id
    LEFT JOIN Reviews ON Reviews.bid = Books.id
    LEFT JOIN GenresBooks ON GenresBooks.bid = Books.id
    LEFT JOIN Genres ON GenresBooks.gid = Genres.id
    group by Books.id
    ORDER BY Books.year DESC
    LIMIT %s OFFSET %s
    '''
    values = []  
    try:
        page = int(request.args.get('page', 1))
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(querry_data, (PER_PAGE, PER_PAGE * (page - 1)))
        values = cursor.fetchall()
        cursor.close()
    except mysql.connector.errors.DatabaseError:
        db.connection().rollback()
        flash(f'При создании обложки произошла ошибка.', 'danger')

    return render_template('index.html', values=values, count=count, page=page)

def get_roles():
    query = 'SELECT * FROM Roles'
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query)
    roles = cursor.fetchall()
    cursor.close()
    return roles

@app.route('/show_book/<int:index>')
def show_book(index):
    querry_data = '''
    SELECT * from Books where id = %s
    '''
    values = []  
    try:
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(querry_data, (index, ))
        values = cursor.fetchone()
        cursor.close()
    except mysql.connector.errors.DatabaseError:
        db.connection().rollback()
        flash(f'При загрузке книги произошла ошибка.', 'danger')

    about = markdown.markdown(values.about)

    querry_data = '''
    SELECT mime, md5 FROM Skins where id = %s
    '''
    try:
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(querry_data, (values.skin, ))
        skin = cursor.fetchone()
        cursor.close()
    except mysql.connector.errors.DatabaseError:
        db.connection().rollback()
        flash(f'При создании обложки произошла ошибка.', 'danger')

    querry_data = '''
    SELECT mark, text, data, login, uid from Reviews 
    LEFT JOIN Users ON Reviews.uid = Users.id
    where bid = %s and status = 2 
    '''
    try:
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(querry_data, (index, ))
        reviews = cursor.fetchall()
        cursor.close()
    except mysql.connector.errors.DatabaseError:
        db.connection().rollback()
        flash(f'При загрузке рецензий произошла ошибка.', 'danger')

    if not current_user.is_anonymous:
        for review in reviews:
            if review.uid == current_user.id:
                my_review = review
                return render_template('show_book.html', values = values, reviews = reviews, skin = skin, about = about, my_review = my_review)
    return render_template('show_book.html', values = values, reviews = reviews, skin = skin, about = about)
