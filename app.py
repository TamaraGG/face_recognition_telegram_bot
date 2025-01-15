import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image  # Для проверки формата файла
from face_recognizer import FaceRecognizer
from db import FaceDatabase
from db import CacheManager
import logging
 
# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
 
# Создание объекта базы данных
DATABASE_PATH = "postgresql://postgres:qUarfUKXDGravsZpXwJGbCWbONgEiGDu@junction.proxy.rlwy.net:57957/railway"
cachemanager = CacheManager()
database = FaceDatabase(DATABASE_PATH, cachemanager)
 
# Создание объекта FaceRecognizer
face_recognizer = FaceRecognizer(database)
 
# Папка для временного хранения фотографий
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
 
def is_jpg_file(file_path):
    """Проверяет, является ли файл изображением в формате JPG."""
    try:
        with Image.open(file_path) as img:
            return img.format.lower() == 'jpeg'
    except Exception as e:
        logger.error(f"Ошибка при проверке формата файла {file_path}: {e}")
        return False
 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    await update.message.reply_text(
        "Привет! Я бот для распознавания лиц. Отправьте мне фото, и я попробую его обработать!"
    )
 
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик документов (файлов)."""
    document = update.message.document
 
    # Проверяем, что файл имеет расширение .jpg
    if not document.file_name.lower().endswith('.jpg'):
        await update.message.reply_text("❌ Пожалуйста, отправьте файл с расширением .jpg. или .img")
        return
 
    try:
        # Скачиваем файл
        file = await context.bot.get_file(document.file_id)
        file_path = os.path.join(DOWNLOAD_FOLDER, document.file_name)
        await file.download_to_drive(file_path)
        logger.info(f"Файл сохранен: {file_path}")
 
        # Проверяем, является ли файл изображением в формате JPG
        if not is_jpg_file(file_path):
            os.remove(file_path)  # Удаляем некорректный файл
            await update.message.reply_text("❌ Файл не является корректным изображением в формате JPG.")
            return
 
        # Обработка изображения (пример работы с FaceRecognizer)
        result = face_recognizer.recognize_and_update(file_path)
 
        # Отправляем результат пользователю
        if isinstance(result, str):
            # Разбираем строку на ключи и значения
            parsed_result = {}
            for line in result.split("\n"):
                if ": " in line:
                    key, value = line.split(": ", 1)
                    parsed_result[key.strip().lower()] = value.strip()
 
            # Проверяем статус
            if parsed_result.get("статус") == "ошибка":
                await update.message.reply_text(f"❌ {parsed_result.get('сообщение', 'Произошла ошибка.')}")
            elif parsed_result.get("статус") == "неоднозначно":
                await update.message.reply_text(f"⚠️ {parsed_result.get('сообщение', 'Не удалось точно определить.')}")
            else:
                await update.message.reply_text(f"✅ Лицо успешно распознано: {result}")
        else:
            # Если результат не строка, предполагаем успешный случай
            await update.message.reply_text(f"✅ Лицо успешно распознано: {result}")
 
    except Exception as e:
        logger.error(f"Ошибка при обработке файла: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке файла.")
 
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик фотографий (отправленных как фото)."""
    try:
        # Сохранение фотографии
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        file_path = os.path.join(DOWNLOAD_FOLDER, f"{photo.file_id}.jpg")
        await file.download_to_drive(file_path)
        logger.info(f"Файл сохранен: {file_path}")
 
        # Проверяем, является ли файл изображением в формате JPG
        if not is_jpg_file(file_path):
            os.remove(file_path)  # Удаляем некорректный файл
            await update.message.reply_text("❌ Файл не является корректным изображением в формате JPG.")
            return
 
        # Обработка изображения (пример работы с FaceRecognizer)
        result = face_recognizer.recognize_and_update(file_path)
        
        # Отправляем результат пользователю
        if isinstance(result, str):
            # Разбираем строку на ключи и значения
            parsed_result = {}
            for line in result.split("\n"):
                if ": " in line:
                    key, value = line.split(": ", 1)
                    parsed_result[key.strip().lower()] = value.strip()
 
            # Проверяем статус
            if parsed_result.get("статус") == "ошибка":
                await update.message.reply_text(f"❌ {parsed_result.get('сообщение', 'Произошла ошибка.')}")
            else:
                await update.message.reply_text(f"✅ Лицо успешно распознано: {result}")
        else:
            # Если результат не строка, предполагаем успешный случай
            await update.message.reply_text(f"✅ Лицо успешно распознано: {result}")
 
    except Exception as e:
        logger.error(f"Ошибка при обработке фото: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке фотографии.")
 
if __name__ == "__main__":
    application = ApplicationBuilder().token("8022943494:AAFrnUb3JIdNaKeML2bMk5HbgfG8MyjvwCw").build()
 
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
 
    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))  # Для файлов
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))  # Для фотографий
 
    # Запуск бота
    application.run_polling()
 