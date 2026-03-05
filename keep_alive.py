import asyncio
import logging
import threading
import time
import requests
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PingService:
    """Сервис для автоматического пинга бота"""
    
    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.running = False
        self.thread = None
    
    def start(self):
        """Запускает пинг в фоновом потоке"""
        self.running = True
        self.thread = threading.Thread(target=self._ping_loop, daemon=True)
        self.thread.start()
        logger.info("✅ Сервис пинга запущен")
    
    def stop(self):
        """Останавливает пинг"""
        self.running = False
        logger.info("⏹ Сервис пинга остановлен")
    
    def _ping_loop(self):
        """Основной цикл пинга"""
        while self.running:
            try:
                # Пингуем через Telegram API
                url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    logger.info(f"✅ Пинг успешен в {time.strftime('%H:%M:%S')}")
                else:
                    logger.warning(f"⚠ Пинг: статус {response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка пинга: {e}")
            
            # Ждем 4 минуты (240 секунд)
            for _ in range(240):
                if not self.running:
                    break
                time.sleep(1)
