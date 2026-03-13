import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
import os
import sys
import aiohttp
from aiohttp import web


# ==================== HEALTH-CHECK ЭНДПОИНТ ====================
async def handle_health(request):
    """Health check endpoint для Render и внешних сервисов"""
    return web.Response(text="Bot is running!")

async def run_web_server():
    """Запускает HTTP сервер для health checks"""
    port = int(os.getenv("PORT", 10000))  # Render сам дает порт
    app = web.Application()
    app.router.add_get('/', handle_health)      # корневой URL
    app.router.add_get('/health', handle_health) # /health
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"⚡ HTTP сервер слушает порт {port}")



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
    )
    
    # Добавляем текст сообщения, если есть
    if message.text:
        user_info += f"<b>Текст:</b> {message.text}"
    else:
        user_info += "📎 <b>Медиафайл</b>"
    
    try:
        # Отправляем информацию админу
        admin_msg = await bot.send_message(
            ADMIN_CHAT_ID, 
            user_info, 
            parse_mode='HTML'
        )
        
        # Сохраняем связь: сообщение админа -> пользователь
        user_messages[admin_msg.message_id] = user.id
        
        # Если есть медиа, пересылаем его отдельно
        if message.photo:
            await bot.send_photo(ADMIN_CHAT_ID, message.photo[-1].file_id, caption=f"Фото от {user.full_name}")
        elif message.document:
            await bot.send_document(ADMIN_CHAT_ID, message.document.file_id, caption=f"Документ от {user.full_name}")
        elif message.video:
            await bot.send_video(ADMIN_CHAT_ID, message.video.file_id, caption=f"Видео от {user.full_name}")
        elif message.audio:
            await bot.send_audio(ADMIN_CHAT_ID, message.audio.file_id, caption=f"Аудио от {user.full_name}")
        elif message.voice:
            await bot.send_voice(ADMIN_CHAT_ID, message.voice.file_id, caption=f"Голосовое от {user.full_name}")
        elif message.sticker:
            await bot.send_sticker(ADMIN_CHAT_ID, message.sticker.file_id)
        elif message.animation:
            await bot.send_animation(ADMIN_CHAT_ID, message.animation.file_id, caption=f"GIF от {user.full_name}")
        
        # Подтверждение пользователю
        await message.answer("✅ Сообщение отправлено администратору. Ожидайте ответа.")
        logger.info(f"Сообщение от {user.id} переслано админу")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке админу: {e}")
        await message.answer("❌ Ошибка при отправке. Попробуйте позже.")

async def handle_admin_message(message: Message):
    """Обработка сообщений от администратора"""
    
    # Проверяем, является ли сообщение ответом на другое сообщение
    if message.reply_to_message:
        original_msg_id = message.reply_to_message.message_id
        
        # Ищем, какому пользователю принадлежит исходное сообщение
        if original_msg_id in user_messages:
            user_id = user_messages[original_msg_id]
            
            # Формируем ответ пользователю
            if message.text:
                reply_text = f"📝 <b>Ответ администратора:</b>\n\n{message.text}"
                await bot.send_message(user_id, reply_text, parse_mode='HTML')
                await message.reply("✅ Ответ отправлен пользователю")
                logger.info(f"Текстовый ответ отправлен пользователю {user_id}")
                
            elif message.photo:
                await bot.send_photo(
                    user_id, 
                    message.photo[-1].file_id, 
                    caption="📝 Ответ администратора (фото)"
                )
                await message.reply("✅ Фото отправлено пользователю")
                
            elif message.document:
                await bot.send_document(
                    user_id, 
                    message.document.file_id, 
                    caption="📝 Ответ администратора (документ)"
                )
                await message.reply("✅ Документ отправлен пользователю")
                
            elif message.video:
                await bot.send_video(
                    user_id, 
                    message.video.file_id, 
                    caption="📝 Ответ администратора (видео)"
                )
                await message.reply("✅ Видео отправлено пользователю")
                
            elif message.sticker:
                await bot.send_sticker(user_id, message.sticker.file_id)
                await message.reply("✅ Стикер отправлен пользователю")
                
            else:
                await message.reply("❌ Неподдерживаемый тип сообщения")
        else:
            await message.reply("❌ Не могу найти пользователя для этого сообщения")
            logger.warning(f"Пользователь не найден для сообщения {original_msg_id}")
    else:
        # Если это не ответ, игнорируем (чтобы не засорять группу)
        pass

async def main():
    """Запуск бота"""
    logger.info("🚀 Запуск бота...")
    
    # Получаем информацию о боте
    me = await bot.get_me()
    logger.info(f"Бот @{me.username} запущен")
    
    # Запускаем HTTP сервер для health checks
    asyncio.create_task(run_web_server())
    
    # Отправляем приветственное сообщение в группу админа
    try:
        await bot.send_message(
            ADMIN_CHAT_ID,
            "🤖 <b>Бот поддержки запущен!</b>\n\n"
            "📝 <b>Инструкция:</b>\n"
            "• Сообщения пользователей будут приходить сюда\n"
            "• Чтобы ответить - используйте <b>Reply</b> на сообщение\n"
            "• Можно отправлять текст, фото, видео, документы\n\n"
            "✅ Бот готов к работе!",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Не удалось отправить приветствие в группу: {e}")
        logger.error("Убедитесь, что бот добавлен в группу и имеет права на отправку сообщений")
    
    # Запускаем поллинг
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹ Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
