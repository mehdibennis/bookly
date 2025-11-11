From python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/


RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install alembic

COPY . /app/

EXPOSE 8000


# Lancer les migrations Alembic avant de démarrer l'app
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
