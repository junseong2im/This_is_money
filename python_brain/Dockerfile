# Python Trading Brain
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Environment variables (override in docker-compose or runtime)
ENV SYMBOL=BTCUSDT
ENV INTERVAL_SEC=60
ENV EXECUTOR_MODE=http

# Run the trading engine
CMD ["python", "main.py"]
