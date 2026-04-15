import pytest, os

os.environ['OTEL_SDK_DISABLED'] = 'true'

DEFAULT_PASSWORDS = {
    "product_test": "Product@123",
    "functional_test": "FuncTest@123"
}

@pytest.fixture
def product_test_password():
    return os.environ.get('PRODUCT_TEST_PASSWORD', DEFAULT_PASSWORDS["product_test"])

@pytest.fixture
def functional_test_password():
    return os.environ.get('FUNCTIONAL_TEST_PASSWORD', DEFAULT_PASSWORDS["functional_test"])