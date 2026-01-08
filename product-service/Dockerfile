FROM python:3.11-slim

ARG ENVIRONMENT
ARG PORT

ENV FLASK_ENV=${ENVIRONMENT}
ENV FLASK_RUN_PORT=${PORT}
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    curl \ 
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /product-service

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

CMD ["python3", "product_app.py"]