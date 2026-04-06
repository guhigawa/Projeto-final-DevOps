#!/bin/bash
#Run unit tests 
echo "Running unit tests"

#User-service
cd user-service
python -m pytest tests/test_unit.py tests/test_validators.py -v
USER_UNIT=$?

cd ../product-service
python -m pytest products_tests/test_product_unit.py products_tests/test_product_validator.py -v
PRODUCT_UNIT=$?

if [ $USER_UNIT -eq 0 ] && [ $PRODUCT_UNIT -eq 0 ]; then
    echo "Unit tests passed successfully"
    exit 0
else
    echo "Unit tests failed"
    exit 1
fi