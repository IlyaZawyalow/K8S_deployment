import psycopg2
from flask import Flask, request, jsonify, render_template
from kubernetes import client, config
from loguru import logger
from psycopg2 import IntegrityError

app = Flask(__name__)

# Функция для получения параметров подключения к базе данных из ConfigMap
def get_db_connection_params_from_configmap():
    try:
        logger.info("Инициализация клиента Kubernetes из текущего контекста.")
        # Инициализация клиента Kubernetes из текущего контекста
        config.load_incluster_config()  # Используем, если запущено внутри Kubernetes

        logger.info("Создаем объект API клиента для работы с ConfigMap")
        # Создаем объект API клиента для работы с ConfigMap
        v1 = client.CoreV1Api()

        # Название ConfigMap с параметрами подключения
        config_map_name = "postgres-db-config"

        logger.info("Получаем данные ConfigMap из текущего namespace")

        # Получаем данные ConfigMap из текущего namespace
        config_map = v1.read_namespaced_config_map(config_map_name, namespace="default")
        logger.info(f"получил ConfigMap: {config_map}")
        # Извлекаем параметры подключения из данных ConfigMap
        db_host = config_map.data.get('DB_HOST', 'postgres-db-lb.default.svc.cluster.local')
        db_port = config_map.data.get('DB_PORT', '5432')
        db_name = config_map.data.get('DB_NAME', 'postgres')
        db_user = config_map.data.get('DB_USER', 'postgres')
        db_password = config_map.data.get('DB_PASSWORD', 'test123')
        logger.info(f'Параметры подключения (в функции get_db_connection_params_from_configmap): db_host {db_host}, db_port {db_port}, db_name {db_name}, db_user {db_user}, db_password {db_password}')
        return db_host, db_port, db_name, db_user, db_password

    except Exception as e:
        logger.error(f"Error retrieving DB connection parameters from ConfigMap: {str(e)}")
        return None

# Функция для создания таблицы "users", если она не существует
def create_users_table_if_not_exists():
    try:
        # Получаем параметры подключения к базе данных из ConfigMap
        db_host, db_port, db_name, db_user, db_password = get_db_connection_params_from_configmap()

        # Устанавливаем соединение с базой данных PostgreSQL
        with psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        ) as conn:
            # Создаем курсор для выполнения SQL запросов
            with conn.cursor() as cursor:
                # Выполняем SQL запрос для создания таблицы "users", если она не существует
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) UNIQUE NOT NULL,
                        email VARCHAR(100) UNIQUE NOT NULL
                    )
                """)
                logger.info("Выполнили SQL запрос для создания таблицы 'users', если она не существует")

    except Exception as e:
        logger.error(f"Error creating 'users' table: {str(e)}")

# Функция для создания новой записи о пользователе в базе данных
def create_user_in_db(name, email):
    try:
        # Создаем таблицу "users", если она не существует
        create_users_table_if_not_exists()

        # Получаем параметры подключения к базе данных из ConfigMap
        db_host, db_port, db_name, db_user, db_password = get_db_connection_params_from_configmap()

        # Устанавливаем соединение с базой данных PostgreSQL
        with psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        ) as conn:
            # Создаем курсор для выполнения SQL запросов
            with conn.cursor() as cursor:
                # Выполняем SQL запрос для создания новой записи о пользователе
                cursor.execute("INSERT INTO users (name, email) VALUES (%s, %s)", (name, email))

                # Фиксируем изменения в базе данных
                conn.commit()
                return True

    except IntegrityError:
        logger.warning('Integrity error occurred. User with the same name or email already exists.')
        return False  # Возвращаем False, чтобы показать, что операция не удалась из-за дубликата
    except Exception as err:
        logger.error(f'Error executing query: {err}')

    return False

# Маршрут для отображения главной страницы
@app.route('/', methods=['GET'])
def show_index():
    return render_template('index.html')

# Маршрут для отображения формы регистрации
@app.route('/register', methods=['GET'])
def show_register_form():
    return render_template('register.html')

# Маршрут для обработки регистрации пользователя
@app.route('/register', methods=['POST'])
def register_user():
    try:
        # Получаем данные о пользователе из тела POST запроса
        data = request.form
        name = data.get('name')
        email = data.get('email')

        if not name or not email:
            raise Exception("Name and email are required for registration")

        # Создаем новую запись о пользователе в базе данных
        if create_user_in_db(name, email):
            return render_template('register.html', message='User registered successfully')
        else:
            return render_template('error.html', error='Failed to register user')

    except Exception as e:
        return render_template('error.html', error=str(e))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
