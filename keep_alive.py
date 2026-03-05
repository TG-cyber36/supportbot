import requests
import time
import os
import logging
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ping_bot():
    """
    Пингует бота через Telegram API
    """
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("Нет BOT_TOKEN для пинга")
        return
    
    # Используем метод getMe для пинга (не требует прав)
    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            logger.info("✅ Пинг успешен")
        else:
            logger.warning(f"⚠️ Пинг вернул код {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Ошибка пинга: {e}")

def start_ping_service():
    """
    Запускает сервис пинга в отдельном потоке
    """
    def ping_loop():
        while True:
            ping_bot()
            # Ждем 5 минут перед следующим пингом
            time.sleep(300)
    
    thread = threading.Thread(target=ping_loop, daemon=True)
    thread.start()
    logger.info("🚀 Сервис пинга запущен (каждые 5 минут)")

if __name__ == "__main__":
    # Для тестирования
    start_ping_service()
    # Бесконечный цикл, чтобы поток работал
    while True:
        time.sleep(60)
