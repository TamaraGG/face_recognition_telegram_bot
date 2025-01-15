import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
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
 
# Функция для отображения начального меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет меню с выбором действий при запуске бота."""
    # Создаем кнопки
    keyboard = [
        [
            InlineKeyboardButton("🗑️ Очистить данные", callback_data='clear_database'),
            InlineKeyboardButton("🤖 Распознать человека", callback_data='recognize_person')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
 
    # Отправляем сообщение с кнопками
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
 
 
# Обработчик нажатий на кнопки
async def handle_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор пользователя из меню."""
    query = update.callback_query
    await query.answer()
 
    if query.data == 'clear_database':
        try:
            # Вызов функции очистки базы данных
            database.clear_database()  # Используем объект database из FaceDatabase
            await query.edit_message_text("✅ База данных успешно очищена.")
        except Exception as e:
            logger.error(f"Ошибка при очистке базы данных: {e}")
            await query.edit_message_text(f"❌ Ошибка при очистке базы данных: {e}")
    elif query.data == 'recognize_person':
        await query.edit_message_text("Пожалуйста, отправьте фотографию для распознавания.")
    else:
        await query.edit_message_text("❌ Неизвестное действие.")
 
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик документов (файлов)."""
    document = update.message.document

    if not document.file_name.lower().endswith('.jpg'):
        await update.message.reply_text("❌ Пожалуйста, отправьте файл с расширением .jpg.")
        return

    try:
        file = await context.bot.get_file(document.file_id)
        file_path = os.path.join(DOWNLOAD_FOLDER, document.file_name)
        await file.download_to_drive(file_path)
        logger.info(f"Файл сохранен: {file_path}")

        if not is_jpg_file(file_path):
            os.remove(file_path)
            await update.message.reply_text("❌ Файл не является корректным изображением в формате JPG.")
            return

        # Обработка изображения
        result = face_recognizer.recognize_and_update(file_path)

        # Отправляем результат
        if isinstance(result, str):
            await update.message.reply_text(result)
        else:
            await update.message.reply_text(f"✅ Лицо успешно распознано: {result}")

    except Exception as e:
        logger.error(f"Ошибка при обработке файла: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке файла.")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)  # Удаляем файл после обработки
            logger.info(f"Файл удален: {file_path}")
 
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик фотографий (отправленных как фото)."""
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        file_path = os.path.join(DOWNLOAD_FOLDER, f"{photo.file_id}.jpg")
        await file.download_to_drive(file_path)
        logger.info(f"Файл сохранен: {file_path}")

        if not is_jpg_file(file_path):
            os.remove(file_path)
            await update.message.reply_text("❌ Файл не является корректным изображением в формате JPG.")
            return

        # Обработка изображения
        result = face_recognizer.recognize_and_update(file_path)

        # Отправляем результат
        if isinstance(result, str):
            await update.message.reply_text(result)
        else:
            await update.message.reply_text(f"✅ Лицо успешно распознано: {result}")

    except Exception as e:
        logger.error(f"Ошибка при обработке фото: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке фотографии.")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)  # Удаляем файл после обработки
            logger.info(f"Файл удален: {file_path}")
 
if __name__ == "__main__":
    application = ApplicationBuilder().token("8022943494:AAFrnUb3JIdNaKeML2bMk5HbgfG8MyjvwCw").build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
 
    application.add_handler(CallbackQueryHandler(handle_menu_choice))
 
    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))  # Для файлов
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))  # Для фотографий
 
    # Запуск бота
    application.run_polling()