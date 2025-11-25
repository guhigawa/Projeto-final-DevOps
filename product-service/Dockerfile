FROM python:3.11-slim

WORKDIR /product-service

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3002
CMD ["python", "product_app.py"]