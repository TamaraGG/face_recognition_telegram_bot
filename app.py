from db import Database

# Инициализация базы данных
db = Database()

# Создание таблицы
db.create_table()

# Добавление нового человека
db.insert_person("John Doe")

# Обновление частоты встреч
db.update_meeting_count("John Doe")

# Закрытие соединения
db.close()
