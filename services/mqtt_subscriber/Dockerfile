FROM python:3.12-slim

WORKDIR /app

COPY services/mqtt_subscriber/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/mqtt_subscriber/app/ ./app/

CMD ["python", "app/main.py"]
