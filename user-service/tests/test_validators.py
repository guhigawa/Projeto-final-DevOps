import pytest
from validators import Validators

class TestValidators:

    def test_validate_email(self):
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",  # Subdomains
            "user+tag@example.org",     # Plus addressing
            "123@test.com",             # Numbers
            "TEST@EXAMPLE.COM",         # Uppercase letters - converted to lowercase
            "user.name+tag@sub.domain.co.uk"  # Complex email case
        ]

        for email in valid_emails:
            is_valid, result = Validators.validate_email(email)
            assert is_valid == True,f"Email should be valid: {email}"
            assert result == email.strip().lower(), f"Email normalization failed: {email}"


    def test_validate_email_invalid(self):
        invalid_emails = [
            ("invalid-email", "Invalid email format"),
            ("@domain.com", "Invalid email format"),      # No local part
            ("user@.com", "Invalid email format"),        # No domain name
            ("user@domain.", "Invalid email format"),     # No TLD (top-level domain)
            ("user@domain.c", "Invalid email format"),    # TLD too short
            ("a" * 260 + "@domain.com", "Email is too long"),  # > 254 chars
            ("", "Email must be a valid string"),          # Empty string
            (None, "Email must be a valid string"),        # None
            (123, "Email must be a valid string"),         # Non-string
            ({"email": "test"}, "Email must be a valid string")  # Dictionary
        ]

        for email,expected_error in invalid_emails:
            is_valid, result = Validators.validate_email(email)
            assert is_valid == False, f"Email should be invalid: {email}"
            assert expected_error in str(result), f"Incorrect error message for {email}: {result}"
    

    def test_validate_password_strong(self):
        strong_passwords = [
            "StrongPass123!",      # 12 chars: Upper, lower, digit
            "AnotherPass456@",     # 14 chars
            "Test123!@#",         # 9 chars with special chars 
            "Min8charsA@",        # Exactly 10 chars 
            "Ab1" + "@" * 17,            # Max length 
        ]

        for password in strong_passwords:
            is_valid, errors = Validators.validate_password(password)
            assert is_valid == True, f"Password should be valid: {password}, error: {errors}"
            assert len(errors) == 0, f"Unexpected errors for {password}: {errors}"
    

    def test_validate_password_weak(self):
        weak_passwords =  [
            # (password, expected_errors)
            ("sh0rt@", ["at least 8 characters"]),
            ("noupper123@", ["uppercase"]),
            ("NOLOWER123@", ["lowercase"]),
            ("NoNumbers@", ["number"]),
            ("Aa1@" + "b" * 20, ["20 characters long"]),  # > 20 chars
            ("", ["valid string"]),
            (None, ["valid string"]),
            (123, ["valid string"]),
            ([], ["valid string"])
        ]

        for password, expected_errors in weak_passwords:
            is_valid, errors = Validators.validate_password(password)
            assert is_valid == False, f"Weak password accepted: {password}"
            error_messages = ' '.join(errors).lower()
            error_found = any(expected_error in error_messages for expected_error in expected_errors)
            assert error_found, f"Expected errors {expected_errors} not found in {errors}"

    def test_sanitize_input(self):
        test_cases = [
            # (input, expected_output)
            ("<script>alert('xss')</script>", "scriptalert(xss)script"),
            ("normal@email.com", "normal@email.com"),
            (";DROP TABLE users; --", "DROP TABLE users --"),  # SQL injection
            ("<img src=x onerror=alert(1)>", "img srcx onerroralert(1)"),
            ("test' OR '1'='1", "test OR 11"),  # SQL injection
            ("normal text", "normal text"),
            ("  spaces  ", "spaces"),           # strip works
            (123, 123),                         # Non-string input remains unchanged
            (None, None),
            ({"key": "value"}, {"key": "value"})  # Dictionary remains unchanged
        ]
        
        for input_text, expected_output in test_cases:
            result = Validators.sanitize_input(input_text)
            assert result == expected_output, f"Sanitization failed: {input_text} -> {result}"
    

    def test_validate_registration_data_valid(self):
        valid_data = {
            "email": "Test@Example.COM", # Uppercase to test normalization
            "password": "StrongPass123@"
        }

        is_valid, result = Validators.validate_registration_data(valid_data)
        assert is_valid == True # Verifies if valid data was introduced
        assert result["email"] == "test@example.com" 
        assert result["password"] == "StrongPass123@"


    def test_validate_registration_data_invalid(self):
        invalid_test_cases = [
            # invalid email
            ({
                "email": "bad-email",
                "password": "StrongPass123@"
            }, "invalid email"),
            
            # weak password
            ({
                "email": "test@example.com", 
                "password": "weak"
            }, "password does not meet requirements"),
            
            # missing password field
            ({
                "email": "test@example.com"
            },"missing required field: password"),
            
            # missing email field
            ({
                "password": "StrongPass123"
            }, "missing required field: email"),
            
            # Empyty data
            ({}, "missing required field: email"),

            # Invalid data type (not a dict)
            ("not-a-dict", "input must be a dictionary"),
            (None, "input must be a dictionary"),
            ([], "input must be a dictionary"),
            (123, "input must be a dictionary")
        ]
        
        for data, expected_error in invalid_test_cases:
            is_valid, result = Validators.validate_registration_data(data)
            assert is_valid == False, f"Invalid data accepted: {data}"
            # Verify if expected error message is in the result
            error_msg = str(result.get("error", result))
            assert expected_error in error_msg, f"incorrect error message: {error_msg}"
    

    def test_validate_registration_data_password_requirements_in_response(self):
        weak_data = {
            "email": "test@example.com",
            "password": "weak"  # Too short
        }

        is_valid, result = Validators.validate_registration_data(weak_data)

        assert is_valid == False
        assert "requirements" in result
        assert "min_length" in result["requirements"]
        assert result["requirements"]["min_length"] == Validators.MIN_PASSWORD_LENGTH