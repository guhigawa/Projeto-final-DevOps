import pytest, os

os.environ['OTEL_SDK_DISABLED'] = 'true'

DEFAULT_PASSWORDS = {
    "valid": "StrongPass123!",
    "wrong": "Wrongpassword@123",
    "strong": "StrongPass@123",
    "default": "Test@1234"
}

WEAK_PASSWORDS = [  "short", #short password
                    "noupper123", #no uppercase letters
                    "NOLOWER123", #no lowercase letters
                    "NoNumber",   #no numbers
                    "",       #empty password
                    "  ",      #only spaces
                    "NoSpecial123", #no special characters
                         ]

@pytest.fixture
def valid_password():
     return os.environ.get('TEST_VALID_PASSWORD', DEFAULT_PASSWORDS["valid"])


@pytest.fixture
def wrong_password():
    return os.environ.get('TEST_WRONG_PASSWORD', DEFAULT_PASSWORDS["wrong"])


@pytest.fixture
def weak_passwords_list():
    return os.environ.get('TEST_WEAK_PASSWORD', WEAK_PASSWORDS)


@pytest.fixture
def strong_password():
    return os.environ.get('TEST_STRONG_PASSWORD', DEFAULT_PASSWORDS["strong"])


@pytest.fixture
def default_password():
    return os.environ.get('TEST_DEFAULT_PASSWORD', DEFAULT_PASSWORDS["default"])