FROM python:3.11-slim

WORKDIR /user-service

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3001
CMD ["python3", "app.py"]