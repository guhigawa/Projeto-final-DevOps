#!/bin/bash
#Run functional tests
echo "Running functional tests"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

cd "$PROJECT_ROOT"

#User-service functional tests
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec -T user-service pytest tests/test_functional.py -v
USER_FUNC_EXIT=$?

#Product-service functional tests
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec -T product-service pytest products_tests/test_product_functional.py -v
PRODUCT_FUNC_EXIT=$?


#Results
if [ $USER_FUNC_EXIT -eq 0 ] && [ $PRODUCT_FUNC_EXIT -eq 0 ]; then
    echo "Functional tests passed successfully"
    exit 0
else
    echo "Functional tests failed"
    exit 1
fi