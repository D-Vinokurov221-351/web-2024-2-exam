from flask import render_template, request, redirect, url_for, flash, Blueprint, send_file, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from check_user import CheckUser
from functools import wraps
import mysql.connector
from app import db
import os
import hashlib

bp_admin = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('У вас недостаточно прав для доступа к данной странице.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def validate(name, about, author, pub, pages, year, genres, userfile):
    errors = {}
    if not name:
        errors['name_message'] = "Название не может быть пустым"
    if not about:
        errors['about_message'] = "Описание не может быть пустым"
    if not author:
        errors['author_message'] = "Автор не должен быть пустым"
    if not pub:
        errors['pub_message'] = "Издательство не должно быть пустым"
    if not pages:
        errors['pages_message'] = "К-во страниц не должно быть пустым"
    if not year or len(year) != 4:
        errors['year_message'] = "Год должен иметь 4 цифры"
    if not genres:
        errors['genres_message'] = "Жанры не могут быть пустыми"
    if not userfile or userfile != 'Ok':
        errors['userfile_message'] = "Обложка не может быть пустой"
    
    return errors

@bp_admin.route('/create', methods = ['POST', 'GET'])
@admin_required
def create():

    query = '''select name from Genres'''
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query)
    genres_start = cursor.fetchall()
    cursor.close()

    if request.method == 'POST':
        name = request.form['name']
        about = request.form['about']
        author = request.form['author']
        pub = request.form['pub']
        pages = request.form['pages']
        year = request.form['year']
        genres = request.form.getlist('genres')
        userfile = request.form.get('userfile')

        md5_hash = hashlib.md5(userfile.read()).hexdigest()
        mime_type = userfile.mimetype
        name_f = f"{md5_hash}.{mime_type.split('/')[1]}"

        

        errors = validate(name, about, author, pub, pages, year, genres, userfile)
        if len(errors.keys()) > 0:
            return render_template('admin/create.html', genres = genres_start)

        try:
            query = '''
                select id from Skins where md5 = %s
                '''
            cursor = db.connection().cursor(named_tuple=True)
            cursor.execute(query, (md5_hash, ))
            skin = cursor.fetchone()
            cursor.close()
            if skin.id == None:
                query = '''
                insert into Skins (md5, mime, name) values (%s, %s, %s)
                '''
                cursor = db.connection().cursor(named_tuple=True)
                cursor.execute(query, (md5_hash, mime_type, name_f))
                db.connection().commit()
                cursor.close()

                query = '''
                select id from Skins where md5 = %s
                '''
                cursor = db.connection().cursor(named_tuple=True)
                cursor.execute(query, (md5_hash, ))
                skin = cursor.fetchone()
                cursor.close()

                userfile.seek(0)

                if not os.path.exists('images'):
                    os.makedirs('images')

                userfile.save(os.path.join('images', name_f))
                flash(f'Обложка {skin.id} успешно создана.', 'success')
        except mysql.connector.errors.DatabaseError:
            db.connection().rollback()
            flash(f'При создании обложки произошла ошибка.', 'danger')
            return render_template('admin/create.html', genres = genres_start)

        try:
            query = '''
                insert into Books (name, about, author, pub, pages, year, skin)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                '''
            cursor = db.connection().cursor(named_tuple=True)
            cursor.execute(query, (name, about, author, pub, pages, year, skin.id))
            db.connection().commit()
            cursor.close()

            query = '''
                select id from Books ORDER BY id DESC LIMIT 1
                '''
            cursor = db.connection().cursor(named_tuple=True)
            cursor.execute(query)
            book = cursor.fetchone()
            cursor.close()
            flash(f'Книга {book.id} успешно создана.', 'success')
        except mysql.connector.errors.DatabaseError:
            db.connection().rollback()
            flash(f'При создании книги произошла ошибка.', 'danger')
            return render_template('admin/create.html', genres = genres_start)


        try:
            for genre in genres:
                query = '''
                    select id from Genres where name = %s
                    '''
                cursor = db.connection().cursor(named_tuple=True)
                cursor.execute(query, (genre, ))
                genreId = cursor.fetchone()
                cursor.close()

                query = '''
                    insert into GenresBooks (bid, gid) Values (%s, %s)
                    '''
                cursor = db.connection().cursor(named_tuple=True)
                cursor.execute(query, (book.id, genreId.id))
                db.connection().commit()
                cursor.close()
            flash(f'Жанры успешно созданы.', 'success')
        except mysql.connector.errors.DatabaseError:
            db.connection().rollback()
            flash(f'При заполнении жанров произошла ошибка.', 'danger')
            return render_template('admin/create.html', genres = genres_start) 
        return render_template('admin/create.html', genres = genres_start) 
    return render_template('admin/create.html', genres = genres_start) 


@bp_admin.route('/edit_book/<int:index>', methods = ['POST', 'GET'])
def edit_book(index):
    query = '''select name from Genres'''
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query)
    genres_start = cursor.fetchall()
    cursor.close()

    query = '''select * from Books where id = %s'''
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query, (index, ))
    book_start = cursor.fetchone()
    cursor.close()

    if request.method == 'POST':
        name = request.form['name']
        about = request.form['about']
        author = request.form['author']
        pub = request.form['pub']
        pages = request.form['pages']
        year = request.form['year']
        genres = request.form.getlist('genres')

        errors = validate(name, about, author, pub, pages, year, genres, 'Ok')
        if len(errors.keys()) > 0:
            return render_template('admin/edit.html', genres = genres_start, book_start=book_start)

        try:
            query = '''
                update Books set name = %s, about = %s, author = %s, pub = %s, pages = %s, year = %s where id = %s
                '''
            cursor = db.connection().cursor(named_tuple=True)
            cursor.execute(query, (name, about, author, pub, pages, year, index))
            db.connection().commit()
            cursor.close()

            query = '''
                select id from Books ORDER BY id DESC LIMIT 1
                '''
            cursor = db.connection().cursor(named_tuple=True)
            cursor.execute(query)
            book = cursor.fetchone()
            cursor.close()
            flash(f'Книга {book.id} успешно создана.', 'success')
        except mysql.connector.errors.DatabaseError:
            db.connection().rollback()
            flash(f'При создании книги произошла ошибка.', 'danger')
            return render_template('admin/edit.html', genres = genres_start, book_start=book_start) 
        
        query = '''
                    delete from GenresBooks where bid = %s
                    '''
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query, (index, ))
        db.connection().commit()
        cursor.close()

        try:
            for genre in genres:
                query = '''
                    select id from Genres where name = %s
                    '''
                cursor = db.connection().cursor(named_tuple=True)
                cursor.execute(query, (genre, ))
                genreId = cursor.fetchone()
                cursor.close()

                query = '''
                    insert into GenresBooks (bid, gid) Values (%s, %s)
                    '''
                cursor = db.connection().cursor(named_tuple=True)
                cursor.execute(query, (book.id, genreId.id))
                db.connection().commit()
                cursor.close()
            flash(f'Жанры успешно созданы.', 'success')
        except mysql.connector.errors.DatabaseError:
            db.connection().rollback()
            flash(f'При заполнении жанров произошла ошибка.', 'danger')
            return render_template('admin/edit.html', genres = genres_start, book_start=book_start) 
        return render_template('admin/edit.html', genres = genres_start, book_start=book_start) 
    return render_template('admin/edit.html', genres = genres_start, book_start=book_start) 

@bp_admin.route('/delete/<int:index>')
def delete_book(index):
    try:
        query = '''
            select name FROM Books WHERE id = %s;
            '''
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query, (index, ))
        book = cursor.fetchone()
        cursor.close()
        flash(f'Книга {index} не успешно удалена.', 'success')
        query = '''
            DELETE FROM Books WHERE id = %s;
            '''
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query, (index, ))
        db.connection().commit()
        cursor.close()
        flash(f'Книга {book.name} успешно удалена.', 'success')
    except mysql.connector.errors.DatabaseError:
        db.connection().rollback()
        flash(f'При удалении книги произошла ошибка.', 'danger')
    return redirect(url_for('index', index = index))
    