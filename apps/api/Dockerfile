FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app

COPY apps/api/requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY apps/api/app ./app
COPY data /data
ENV VENUE_DATA_PATH=/data/venues/unity-stadium.json

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
