import psycopg2
from flask import Flask, request, render_template
from loguru import logger
from psycopg2 import IntegrityError
import os


app = Flask(__name__)


def get_db_connection_params_from_configmap():
    """
    Функция для получения параметров подключения к базе данных из ConfigMap
    """
    try:
        db_password = os.environ.get('POSTGRES_PASSWORD')
        db_host = os.environ.get('DB_HOST')
        db_port = os.environ.get('DB_PORT')
        db_name = os.environ.get('DB_NAME')
        db_user = os.environ.get('DB_USER')       
        return db_host, db_port, db_name, db_user, db_password

    except Exception as e:
        logger.error(f"Error retrieving DB connection parameters from ConfigMap: {str(e)}")
        return None

def create_users_table_if_not_exists():
    """
    Функция для создания таблицы "users", если она не существует
    """
    try:
        # Получаем параметры подключения к базе данных из ConfigMap
        db_host, db_port, db_name, db_user, db_password = get_db_connection_params_from_configmap()

        with psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) UNIQUE NOT NULL,
                        email VARCHAR(100) UNIQUE NOT NULL
                    )
                """)

    except Exception as e:
        logger.error(f"Error creating 'users' table: {str(e)}")

def create_user_in_db(name, email):
    """
    Функция для создания новой записи о пользователе в базе данных
    """
    try:
        create_users_table_if_not_exists()

        # Получаем параметры подключения к базе данных из ConfigMap
        db_host, db_port, db_name, db_user, db_password = get_db_connection_params_from_configmap()

        with psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO users (name, email) VALUES (%s, %s)", (name, email))
                conn.commit()
                return True
    except IntegrityError as e:
        logger.warning(f'User with the same name or email already exists: {e}')
        return False
    except Exception as e:
        logger.error(f'Error executing query: {e}')
        return False

@app.route('/', methods=['GET'])
def show_index():
    return render_template('index.html')


@app.route('/register', methods=['GET'])
def show_register_form():
    return render_template('register.html')


@app.route('/show_users', methods=['GET'])
def show_users():
    try:
        # Получаем параметры подключения к базе данных из ConfigMap
        db_host, db_port, db_name, db_user, db_password = get_db_connection_params_from_configmap()

        with psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, name, email FROM users")
                rows = cursor.fetchall()

                # Формируем список пользователей для передачи в шаблон
                users = [{'id': row[0], 'name': row[1], 'email': row[2]} for row in rows]
        return render_template('users.html', users=users)

    except Exception as e:
        return render_template('error.html', error=str(e))
    

@app.route('/register', methods=['POST'])
def register_user():
    try:
        # Получаем данные о пользователе из тела POST запроса
        data = request.form
        name = data.get('name')
        email = data.get('email')

        if not name or not email:
            raise Exception("Name and email are required for registration")

        # Пытаемся создать нового пользователя
        if create_user_in_db(name, email):
            return render_template('register.html', message='User registered successfully')
        else:
            return render_template('register.html', message='User already exists')

    except Exception as e:
        return render_template('error.html', error=str(e))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)