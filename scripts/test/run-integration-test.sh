#!/bin/bash
echo "Running integration tests"

cd user-service
python -m pytest tests/test_integration.py -v
USER_INT=$?

cd ../product-service
python -m pytest products_tests/test_product_integration.py -v
PRODUCT_INT=$?

if [ $USER_INT -eq 0 ] && [ $PRODUCT_INT -eq 0 ]; then
    echo "Integration tests passed successfully"
    exit 0
else
    echo "Integration tests failed"
    exit 1
fi