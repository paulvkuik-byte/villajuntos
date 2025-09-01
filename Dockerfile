FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8080
ENV SECRET_KEY=change-me
ENV DATABASE_URL=sqlite:///app.db
CMD exec gunicorn -w 2 -k gthread --threads 8 -b 0.0.0.0:$PORT app:app
