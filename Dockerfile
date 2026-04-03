FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends libolm-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py commands.py storage.py config.py .env ./

CMD ["python", "bot.py"]
