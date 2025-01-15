# Проект по распознаванию лиц
Этот проект использует библиотеки для распознавания лиц, взаимодействия с базой данных PostgreSQL и создания бота для Telegram. Все зависимости, необходимые для работы проекта, перечислены в файле `requirements.txt`.
## Структура проекта
- **face-recognition**: для распознавания лиц.
- **PostgreSQL**: для хранения данных.
- **python-telegram-bot**: для взаимодействия с Telegram-ботом.
- **SQLAlchemy**: для работы с базой данных через ORM.
## Установка зависимостей
Для начала нужно создать виртуальное окружение и установить зависимости, указанные в файле `requirements.txt`. 

### Шаги по установке
1. Создайте виртуальное окружение:
   ```bash
   python -m venv venv
   ```
2. Активируйте виртуальное окружение.

   Для Windows:
   ```bash
   venv\Scripts\activate
   ```
   Для macOS/Linux:
   ```bash
   source venv/bin/activate
   ```
4. Установите зависимости. Они находятся в файле requirements.txt, установите их с помощью команды:
   ```bash
   pip install -r requirements.txt
   ```
6. Убедитесь, что у вас установлены необходимые системные библиотеки для работы с библиотеками dlib и face-recognition (если вы работаете в Linux или macOS).
7. Установите и настройте PostgreSQL, если вы используете его для хранения данных.  
Для начала создайте базу данных и пользователя в PostgreSQL:
   ```bash
   sudo -u postgres psql
   CREATE DATABASE your_db_name;
   CREATE USER your_db_user WITH PASSWORD 'your_password';
   ALTER ROLE your_db_user SET client_encoding TO 'utf8';
   ALTER ROLE your_db_user SET default_transaction_isolation TO 'read committed';
   ALTER ROLE your_db_user SET timezone TO 'UTC';
   GRANT ALL PRIVILEGES ON DATABASE your_db_name TO your_db_user;
   ```
Настройте параметры подключения в коде.

## Запуск проекта
1. Подключение к базе данных  
Настройте параметры подключения к базе данных PostgreSQL в вашем проекте.  
Пример конфигурации для SQLAlchemy:  
   ```python
   DATABASE_URL = "postgresql://your_db_user:your_password@localhost/your_db_name"
   ```
3. Настройка Telegram-бота  
Создайте бота через BotFather и получите токен. Убедитесь, что добавили его в код:  
   ```python
   from telegram import Bot
   
   TOKEN = "your_telegram_bot_token"
   bot = Bot(token=TOKEN)
   ```
3. Запуск приложения  
Для запуска проекта просто выполните основной скрипт:  
   ```bash
   python main.py
   ```
Замените main.py на имя вашего основного файла, если оно отличается.
