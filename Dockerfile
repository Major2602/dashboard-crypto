FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей (если нужны для сборки pandas/scikit)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir .[dev]

COPY data/ data/
COPY src/ src/

# Переменные окружения для продакшена
ENV PYTHONPATH=/app
ENV DASH_DEBUG=False
ENV HOST=0.0.0.0
ENV PORT=8080

EXPOSE 8080

CMD ["gunicorn", "src.dashboard.app:server", "--workers=4", "--threads=2", "--timeout=120", "--bind", "0.0.0.0:8080"]
