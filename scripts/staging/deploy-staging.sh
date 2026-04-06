#!/bin/bash
set -e

#Find the root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "script dir = $SCRIPT_DIR"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
echo "Project root = $PROJECT_ROOT"

#Deploy the staging environment

#Clean up previous staging environment
echo "Cleaning up previous staging environment"
docker-compose -f docker-compose.staging.yml --env-file .env.staging down -v 2>/dev/null || true

cd "$PROJECT_ROOT"

#Copy requirements to the service directory
cp requirements/staging_requirements.txt user-service/requirements.txt
cp requirements/staging_requirements.txt product-service/requirements.txt

#Build and start the staging environment
echo "building and starting the staging environment"
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d --build 
sleep 30 

#verify that the services are healthy
echo "Verifying that the services are healthy"

USER_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:4001/health)
if [ "$USER_HEALTH" -eq 200 ]; then
    echo "user-service: OK(HTTP $USER_HEALTH)"
else
    echo "user-service: FAIL(HTTP $USER_HEALTH)"
    echo "user-service logs:"
    docker-compose -f docker-compose.staging.yml --env-file .env.staging logs --tail=20 user-service
    exit 1
fi

PRODUCT_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:4002/health)
if [ "$PRODUCT_HEALTH" -eq 200 ]; then
    echo "product-service: OK(HTTP $PRODUCT_HEALTH)"
else
    echo "product-service: FALHOU(HTTP $PRODUCT_HEALTH)"
    echo "Logs do product-service:"
    docker-compose -f docker-compose.staging.yml --env-file .env.staging logs --tail=20 product-service
    exit 1
fi

echo "Staging deployed successful"
