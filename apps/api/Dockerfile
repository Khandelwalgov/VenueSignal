FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app

COPY apps/api/requirements-base.txt apps/api/requirements-production.txt ./
RUN python -m pip install --no-cache-dir -r requirements-production.txt
COPY apps/api/app ./app
COPY data /data
ENV VENUE_DATA_PATH=/data/venues/unity-stadium.json

RUN useradd --system --uid 10001 --no-create-home venuesignal
USER 10001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-server-header"]
