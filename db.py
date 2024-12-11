import psycopg2
import os

class Database:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.connect()

    def connect(self):
        # Подключаемся к базе данных с использованием строки подключения
        try:
            self.conn = psycopg2.connect(os.getenv("DATABASE_URL"))
            self.cursor = self.conn.cursor()
            print("Connected to the database successfully.")
        except Exception as e:
            print("Error connecting to the database:", e)

    def create_table(self):
        """Создание таблицы для хранения информации о лицах."""
        try:
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS face_meetings (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                meeting_count INT DEFAULT 0
            )
            """)
            self.conn.commit()
        except Exception as e:
            print("Error creating table:", e)

    def insert_person(self, name):
        """Добавление человека в базу данных."""
        try:
            self.cursor.execute("INSERT INTO face_meetings (name) VALUES (%s) RETURNING id", (name,))
            self.conn.commit()
        except Exception as e:
            print("Error inserting person:", e)

    def update_meeting_count(self, name):
        """Обновление количества встреч человека."""
        try:
            self.cursor.execute("""
                UPDATE face_meetings
                SET meeting_count = meeting_count + 1
                WHERE name = %s
            """, (name,))
            self.conn.commit()
        except Exception as e:
            print("Error updating meeting count:", e)

    def close(self):
        """Закрытие соединения с базой данных."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
