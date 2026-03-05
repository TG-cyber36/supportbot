import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
import os
import sys
from keep_alive import PingService  # Импортируем наш пингер

# Настройки из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

# Проверка настроек
if not BOT_TOKEN:
    print("❌ Ошибка: Нет BOT_TOKEN!")
    sys.exit(1)
if not ADMIN_CHAT_ID:
    print("❌ Ошибка: Нет ADMIN_CHAT_ID!")
    sys.exit(1)

try:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)
except ValueError:
    print("❌ Ошибка: ADMIN_CHAT_ID должен быть числом!")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Запускаем сервис пинга
pinger = PingService(BOT_TOKEN)
pinger.start()

# Хранилище связей
user_messages = {}

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        "👋 Привет! Я бот поддержки.\n"
        "Напишите ваш вопрос, и я передам его администратору."
    )
    logger.info(f"Пользователь {message.from_user.id} запустил бота")

@dp.message(Command("ping"))
async def cmd_ping(message: Message):
    """Команда для проверки работы бота"""
    await message.answer("🏓 Pong! Бот работает")

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """Статистика для администратора"""
    if message.chat.id == ADMIN_CHAT_ID:
        await message.answer(f"📊 Активных диалогов: {len(user_messages)}")

@dp.message()
async def handle_messages(message: Message):
    """Обработчик всех сообщений"""
    chat_id = message.chat.id
    
    # Сообщение от администратора
    if chat_id == ADMIN_CHAT_ID:
        await handle_admin_message(message)
    else:
        # Сообщение от пользователя
        await handle_user_message(message)

async def handle_user_message(message: Message):
    """Обработка сообщений от пользователей"""
    user = message.from_user
    
    # Формируем информацию о пользователе
    user_info = (
        f"📨 <b>НОВОЕ СООБЩЕНИЕ</b>\n"
        f"{'─' * 30}\n"
        f"<b>От:</b> {user.full_name}\n"
        f"<b>ID:</b> <code>{user.id}</code>\n"
        f"<b>Username:</b> @{user.username or 'нет'}\n"
        f"{'─' * 30}\n"
        f"<b>Текст:</b> {message.text or '📎 Медиафайл'}"
    )
    
    try:
        # Отправляем информацию админу
        admin_msg = await bot.send_message(
            ADMIN_CHAT_ID, 
            user_info, 
            parse_mode='HTML'
        )
        
        # Сохраняем связь
        user_messages[admin_msg.message_id] = user.id
        
        # Если есть медиа, пересылаем
        if message.photo:
            await bot.send_photo(ADMIN_CHAT_ID, message.photo[-1].file_id)
        elif message.document:
            await bot.send_document(ADMIN_CHAT_ID, message.document.file_id)
        
        # Подтверждение пользователю
        await message.answer("✅ Сообщение отправлено администратору. Ожидайте ответа.")
        logger.info(f"Сообщение от {user.id} переслано админу")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке админу: {e}")
        await message.answer("❌ Ошибка при отправке. Попробуйте позже.")

async def handle_admin_message(message: Message):
    """Обработка сообщений от администратора"""
    
    if message.reply_to_message:
        original_msg_id = message.reply_to_message.message_id
        
        if original_msg_id in user_messages:
            user_id = user_messages[original_msg_id]
            
            try:
                reply_text = f"📝 <b>Ответ администратора:</b>\n\n{message.text}" if message.text else "📎 Ответ с медиафайлом"
                
                await bot.send_message(
                    user_id,
                    reply_text,
                    parse_mode='HTML'
                )
                
                await message.reply("✅ Ответ отправлен пользователю")
                logger.info(f"Ответ отправлен пользователю {user_id}")
                
            except Exception as e:
                await message.reply(f"❌ Ошибка при отправке: {e}")
        else:
            await message.reply("❌ Не могу найти пользователя")

async def main():
    """Запуск бота"""
    logger.info("🚀 Запуск бота...")
    
    # Удаляем вебхук
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем поллинг
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹ Бот остановлен")
        pinger.stop()
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        pinger.stop()
