from flask import Flask, request, jsonify, render_template
from kubernetes import client, config
import os
import psycopg2
from loguru import logger

app = Flask(__name__)

# Функция для получения параметров подключения к базе данных из ConfigMap
def get_db_connection_params_from_configmap():
    try:
        logger.info("Инициализация клиента Kubernetes из текущего контекста. ")
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
        logger.info(f'Параметры подключени (в фукнции get_db_connection_params_from_configmap): db_host {db_host}, db_port {db_port}, db_name {db_name}, db_user {db_user}, db_password {db_password}')
        return db_host, db_port, db_name, db_user, db_password

    except Exception as e:
        logger.error(f"Error retrieving DB connection parameters from ConfigMap: {str(e)}")
        return None

# Функция для создания новой записи о пользователе в базе данных
def create_user_in_db(name, email):
    try:
        # Получаем параметры подключения к базе данных из ConfigMap
        db_host, db_port, db_name, db_user, db_password = get_db_connection_params_from_configmap()
        logger.info(f'Параметры подключени: db_host {db_host}, db_port {db_port}, db_name {db_name}, db_user {db_user}, db_password {db_password}')
        if not all([db_host, db_port, db_name, db_user, db_password]):
            raise Exception("Failed to retrieve DB connection parameters from ConfigMap")

        # Устанавливаем соединение с базой данных PostgreSQL
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )

        # Создаем курсор для выполнения SQL запросов
        cursor = conn.cursor()

        # Выполняем SQL запрос для создания новой записи о пользователе
        cursor.execute("INSERT INTO users (name, email) VALUES (%s, %s)", (name, email))

        # Фиксируем изменения в базе данных
        conn.commit()

        # Закрываем курсор и соединение
        cursor.close()
        conn.close()

        return True

    except Exception as e:
        logger.error(f"Не удалось добавить пользователя в базу данных: {str(e)}")
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