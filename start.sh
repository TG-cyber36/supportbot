#!/bin/bash

echo "🚀 Запуск бота поддержки..."

# Проверка переменных окружения
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ Ошибка: BOT_TOKEN не установлен!"
    exit 1
fi

if [ -z "$ADMIN_CHAT_ID" ]; then
    echo "❌ Ошибка: ADMIN_CHAT_ID не установлен!"
    exit 1
fi

echo "✅ Переменные окружения проверены"

# Запускаем бота
echo "🤖 Запуск бота..."
python bot.py
