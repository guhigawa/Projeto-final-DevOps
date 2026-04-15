#!/bin/bash
echo "Running integration tests"

cd /home/ubuntu/Downloads/Projeto_final

pytest tests/user/test_integration.py -v
USER_INT=$?

pytest tests/product/test_product_integration.py -v
PRODUCT_INT=$??

if [ $USER_INT -eq 0 ] && [ $PRODUCT_INT -eq 0 ]; then
    echo "Integration tests passed successfully"
    exit 0
else
    echo "Integration tests failed"
    exit 1
fi