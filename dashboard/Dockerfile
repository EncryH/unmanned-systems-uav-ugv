FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY dashboard/app.py .
COPY dashboard/templates ./templates

CMD ["python", "app.py"]
