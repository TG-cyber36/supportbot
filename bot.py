import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
import os
import sys
from aiohttp import web  # Добавляем aiohttp для health check

# Настройки из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
PORT = int(os.getenv('PORT', 10000))  # Render присваивает порт автоматически

# Проверка настроек
if not BOT_TOKEN or not ADMIN_CHAT_ID:
    print("❌ Ошибка: Не все переменные окружения установлены!")
    sys.exit(1)

ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=BTOKEN)
dp = Dispatcher()

# Хранилище связей
user_messages = {}

# Создаем aiohttp приложение для health check
app = web.Application()

async def health_check(request):
    """Эндпоинт для проверки здоровья"""
    return web.Response(text="OK", status=200)

app.router.add_get('/healthcheck', health_check)
app.router.add_get('/', health_check)  # На всякий случай

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я бот поддержки.\n"
        "Напишите ваш вопрос, и я передам его администратору."
    )

@dp.message()
async def handle_messages(message: Message):
    """Обработчик всех сообщений"""
    chat_id = message.chat.id
    
    if chat_id == ADMIN_CHAT_ID:
        await handle_admin_message(message)
    else:
        await handle_user_message(message)

async def handle_user_message(message: Message):
    """Обработка сообщений от пользователей"""
    user = message.from_user
    
    user_info = (
        f"📨 <b>НОВОЕ СООБЩЕНИЕ</b>\n"
        f"{'─' * 30}\n"
        f"<b>От:</b> {user.full_name}\n"
        f"<b>ID:</b> <code>{user.id}</code>\n"
        f"<b>Username:</b> @{user.username or 'нет'}\n"
        f"{'─' * 30}\n"
        f"{message.text or '📎 Медиафайл'}"
    )
    
    try:
        admin_msg = await bot.send_message(ADMIN_CHAT_ID, user_info, parse_mode='HTML')
        user_messages[admin_msg.message_id] = user.id
        
        if message.photo:
            await bot.send_photo(ADMIN_CHAT_ID, message.photo[-1].file_id)
        
        await message.answer("✅ Сообщение отправлено администратору. Ожидайте ответа.")
        logger.info(f"Сообщение от {user.id} переслано админу")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer("❌ Ошибка при отправке. Попробуйте позже.")

async def handle_admin_message(message: Message):
    """Обработка сообщений от администратора"""
    if message.reply_to_message:
        original_msg_id = message.reply_to_message.message_id
        
        if original_msg_id in user_messages:
            user_id = user_messages[original_msg_id]
            
            try:
                reply_text = f"📝 <b>Ответ администратора:</b>\n\n{message.text}"
                await bot.send_message(user_id, reply_text, parse_mode='HTML')
                await message.reply("✅ Ответ отправлен пользователю")
            except Exception as e:
                await message.reply(f"❌ Ошибка: {e}")

async def run_bot():
    """Запуск бота и веб-сервера параллельно"""
    # Удаляем вебхук
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем поллинг бота
    asyncio.create_task(dp.start_polling(bot))
    
    # Запускаем веб-сервер для health check
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    
    logger.info(f"🚀 Бот запущен на порту {PORT}")
    
    # Держим сервер запущенным
    await asyncio.Event().wait()

if __name__ == '__main__':
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("⏹ Бот остановлен")
