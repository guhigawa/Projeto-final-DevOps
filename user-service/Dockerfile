FROM python:3.11-alpine

ARG ENVIRONMENT
ARG PORT

ENV FLASK_ENV=${ENVIRONMENT}
ENV FLASK_RUN_PORT=${PORT}
ENV PYTHONUNBUFFERED=1
ENV JAEGER_AGENT_HOST=jaeger.monitoring.svc.cluster.local
ENV JAEGER_AGENT_PORT=6831
ENV OTEL_SERVICE_NAME=user-service
ENV OTEL_TRACES_EXPORTER=jaeger

RUN apk update && apk upgrade && \
    apk add --no-cache \
    curl \
    gcc \
    musl-dev \
    mariadb-dev \
    pkgconfig \
    build-base

WORKDIR /user-service

COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    # Remove versões vulneráveis do _vendor/ do setuptools
    rm -rf /usr/local/lib/python3.11/site-packages/setuptools/_vendor/jaraco.context-5.3.0.dist-info && \
    rm -rf /usr/local/lib/python3.11/site-packages/setuptools/_vendor/jaraco_context-5.3.0.dist-info && \
    rm -rf /usr/local/lib/python3.11/site-packages/setuptools/_vendor/wheel-0.45.1.dist-info

COPY . .

RUN addgroup -S app && adduser -S app -G app && \
    chown -R app:app /user-service
    
USER app

EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

CMD ["python3", "app.py"]