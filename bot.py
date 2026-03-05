import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
import os
import sys

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

# Хранилище связей (в памяти)
user_messages = {}  # message_id -> user_id
user_chats = {}     # user_id -> last_message_id

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
    """Команда для пинга бота"""
    await message.answer("🏓 Pong! Бот работает")

@dp.message()
async def handle_messages(message: Message):
    """Обработчик всех сообщений"""
    chat_id = message.chat.id
    
    # Сообщение от администратора (из группы)
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
        f"<b>Ссылка:</b> tg://user?id={user.id}\n"
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
        user_chats[user.id] = admin_msg.message_id
        
        # Если есть медиа, пересылаем
        if message.photo:
            await bot.send_photo(ADMIN_CHAT_ID, message.photo[-1].file_id)
        elif message.document:
            await bot.send_document(ADMIN_CHAT_ID, message.document.file_id)
        elif message.video:
            await bot.send_video(ADMIN_CHAT_ID, message.video.file_id)
        elif message.audio:
            await bot.send_audio(ADMIN_CHAT_ID, message.audio.file_id)
        elif message.voice:
            await bot.send_voice(ADMIN_CHAT_ID, message.voice.file_id)
        elif message.sticker:
            await bot.send_sticker(ADMIN_CHAT_ID, message.sticker.file_id)
        
        # Подтверждение пользователю
        await message.answer("✅ Сообщение отправлено администратору. Ожидайте ответа.")
        logger.info(f"Сообщение от {user.id} переслано админу")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке админу: {e}")
        await message.answer("❌ Ошибка при отправке. Попробуйте позже.")

async def handle_admin_message(message: Message):
    """Обработка сообщений от администратора"""
    
    # Проверяем, является ли сообщение ответом
    if message.reply_to_message:
        original_msg_id = message.reply_to_message.message_id
        
        # Ищем пользователя
        if original_msg_id in user_messages:
            user_id = user_messages[original_msg_id]
            
            # Получаем текст ответа
            reply_text = f"📝 <b>Ответ администратора:</b>\n\n{message.text}" if message.text else "📎 Ответ с медиафайлом"
            
            try:
                # Отправляем ответ пользователю
                await bot.send_message(
                    user_id,
                    reply_text,
                    parse_mode='HTML'
                )
                
                # Подтверждение админу
                await message.reply("✅ Ответ отправлен пользователю")
                logger.info(f"Ответ отправлен пользователю {user_id}")
                
            except Exception as e:
                error_msg = f"❌ Ошибка при отправке: {e}"
                await message.reply(error_msg)
                logger.error(f"Ошибка отправки ответа: {e}")
        else:
            await message.reply("❌ Не могу найти пользователя для этого сообщения")
    else:
        # Игнорируем обычные сообщения в группе
        pass

async def main():
    """Запуск бота"""
    logger.info("Запуск бота...")
    
    # Удаляем вебхук (на всякий случай)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем поллинг
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
