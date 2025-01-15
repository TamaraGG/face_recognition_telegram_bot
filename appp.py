import numpy as np
from db import FaceDatabase
from face_recognizer import FaceRecognizer


# URL для подключения к PostgreSQL (замените данные на свои)
DATABASE_URL = "postgresql://postgres:qUarfUKXDGravsZpXwJGbCWbONgEiGDu@junction.proxy.rlwy.net:57957/railway"

database = FaceDatabase(DATABASE_URL)
recognizer = FaceRecognizer(database)
# Замените 'path_to_image.jpg' на путь к вашему изображению

result1 = recognizer.recognize_and_update('example_photos/1.jpg')
result2 = recognizer.recognize_and_update('example_photos/5.jpg')
result3 = recognizer.recognize_and_update('example_photos/10.jpg')
print(result1)
print(result2)
print(result3)