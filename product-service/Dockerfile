FROM python:3.11-slim

ARG ENVIRONMENT
ARG PORT

ENV FLASK_ENV=${ENVIRONMENT}
ENV FLASK_RUN_PORT=${PORT}
ENV PYTHONUNBUFFERED=1
ENV JAEGER_AGENT_HOST=jaeger.monitoring.svc.cluster.local
ENV JAEGER_AGENT_PORT=6831
ENV OTEL_SERVICE_NAME=product-service
ENV OTEL_TRACES_EXPORTER=jaeger

RUN apt-get update && apt-get install -y \
    curl \ 
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /product-service

COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir setuptools==79.0.1 wheel==0.46.3 && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --upgrade wheel jaraco.context


COPY . .

RUN addgroup --system app && adduser --system --group app && \
    chown -R app:app /product-service
    
USER app

EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

CMD ["python3", "product_app.py"]