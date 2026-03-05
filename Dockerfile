# Явно указываем версию Python 3.11
FROM python:3.11-slim-bookworm

# Устанавливаем переменные окружения для Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Сначала копируем только requirements для кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы
COPY . .

# Команда запуска
CMD ["python", "bot.py"]
