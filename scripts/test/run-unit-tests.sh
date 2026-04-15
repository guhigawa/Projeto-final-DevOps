#!/bin/bash
#Run unit tests 
echo "Running unit tests"

cd /home/ubuntu/Downloads/Projeto_final

#User-service
pytest tests/user/test_unit.py tests/user/test_validators.py -v
USER_UNIT=$?

pytest tests/product/test_product_unit.py tests/product/test_product_validator.py -v
PRODUCT_UNIT=$?

if [ $USER_UNIT -eq 0 ] && [ $PRODUCT_UNIT -eq 0 ]; then
    echo "Unit tests passed successfully"
    exit 0
else
    echo "Unit tests failed"
    exit 1
fi