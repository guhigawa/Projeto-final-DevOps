import pytest
from product_validator import ProductValidator

class TestProductValidator:


    def test_validate_product_name_valid(self):
        valid_prodcuts =[
            "Laptop Pro",
            "iPhone 15",
            "Coffee Maker - Deluxe",
            "Book (Learning Python)",
            "A" * 254, #Max character
            "123 Test Product",  # Numbers
            "TEST PRODUCT",      # Uppercase - converted to lowercase
            "product with, commas and 'quotes'",  # Complex case
        ]

        for name in valid_prodcuts:
            is_valid, result = ProductValidator.validate_product(name)
            assert is_valid == True, f"Product name should be valid: {name}"
            assert result == name.strip().lower(), f"product_name normalization failed: {name}"
    

    def test_validate_product_name_invalid(self):
        invalid_products = [
            ("", "Product name cannot be empty"),
            ("  ", "Product name cannot be empty"),
            ("a" * 255, "Product name too long"),
            ("Product<script>", "Invalid product name format"),#invalid characters usage
            ("Product; DROP TABLE;", "Invalid product name format"), #SQL injection
            (None,"Product name must be a valid string"),
            (123, "Product name must be a valid string"),
            ({"name": "test"},"Product name must be a valid string") #dictionary
        ]

        for name,expected_error in invalid_products:
            is_valid, result = ProductValidator.validate_product(name)
            assert is_valid == False, f"Product name should be invalid"
            assert expected_error in str(result), f"Incorrect error message for {name}: {result}"

    
    def test_validate_product_price(self):
        valid_prices = [
            (29.99, 29.99),      # Standard price
            ("49.50", 49.5),     # String price
            (0.00, 0.0),         # Zero price
            (9999.99, 9999.99),  # Max price
            ("0", 0.0),          # Zero as string
            (123, 123.0),        # Integer price
        ]

        for price, expected_result in valid_prices:
            is_valid, result = ProductValidator.validate_product_price(price)
            assert is_valid == True, f"Product price should be valid:{price}"
            assert round(result, 2) == round(expected_result,2), f"Expected {expected_result}, got {result}"
    

    def test_validate_product_price_invalid(self):
        invalid_prices = [
            ("texto", "Price must be a valid number"),
            (10000, "Price must be lower than"),
            (-1.00, "Price must be at least"),
            ("", "Price must be a valid number"),
            (None,"Price must be a valid number"),
            ([], "Price must be a valid number")
        ]

        for price, expected_errors in invalid_prices:
            is_valid, errors = ProductValidator.validate_product_price(price)
            assert is_valid == False, f"Invalid price accepted:{price}"
            error_messages = errors.lower()
            expected_errors_normalized = expected_errors.lower()
            assert expected_errors_normalized in error_messages, f"Expected errors {expected_errors} not found in {errors}"
    

    def test_validate_product_quantity_valid(self):
        valid_quantities = [
            (10, 10),      # Standard quantity
            ("5", 5),      # String quantity
            (0, 0),        # Zero quantity
            (9999, 9999),  # Max quantity
            ("0", 0),      # Zero as string
            ("", 0)#Should return 0
        ]

        for quantity, expected_result in valid_quantities:
            is_valid, result = ProductValidator.validate_product_quantity(quantity)
            assert is_valid == True, f"quantity should be valid:{result}"
            assert result == expected_result, f"Expected {expected_result}, got {result}"
    

    def test_validate_product_quantity_invalid(self):
        invalid_quantities = [
            (-1, "Quantity must be at least"),
            (10000, "Quantity must be lower"),
            ("invalid", "Quantity must be a valid integer"),
            (29.99, "Quantity must be a valid integer"),  # Float
            ("29.99", "Quantity must be a valid integer") # Float as string should be invalid
        ]

        for quantity, expected_result in invalid_quantities:
            is_valid, result = ProductValidator.validate_product_quantity(quantity)
            assert is_valid == False, f"Quantity should be invalid for : {quantity}"
            assert expected_result in str(result), f"Incorrect error message for {quantity}: {result}"
        
    
    def test_validate_product_description(self):
        test_description = [
            # (description, expected_valid, expected_error_keyword)
            ("", True, ""),  # Empty string valid
            (None, True, ""),  # None valid (treated as empty)
            ("Good description", True, ""),  # Normal description
            ("A" * 2001, False, "Description too long"),  # Too long
            (123, False, "Description must be a string"),  # Non-string
            ([], False, "Description must be a string"),  # List
        ]

        for description, expected_valid, expected_result in test_description:
            is_valid, result = ProductValidator.validate_product_description(description)

            if expected_valid:
                assert is_valid == True, f"Description should be valid:{description}"
                if description is None:
                    assert result == "", f"None should return empyty string, got: {description}"
                else:
                    assert result == description.strip(), f"Descrition not returne correctly: {result}"
            
            else:
                assert is_valid == False, f"Description should be invalid: {description}"
                assert expected_result in str(result), f"Incorrect error for {description}:{result}"
    

    def test_sanitize_input(self):
        test_input = [
            # (input, expected_output)
            ("normal text", "normal text"),
            ("<script>alert('xss')</script>", "scriptalert(xss)script"),
            ('Test "quotes"', "Test quotes"),
            (";DROP TABLE users;", "DROP TABLE users"),  # SQL injection
            ("<img src=x onerror=alert(1)>", "img srcx onerroralert(1)"),
            ("test' OR '1'='1", "test OR 11"),  # SQL injection
            ("   spaces   ", "spaces"),  # strip works
            ("A&B<C>D", "A&BCD"),  # Multiple dangerous chars
            (123, 123),  # Non-string input remains unchanged
            (None, None),
            ({"key": "value"}, {"key": "value"})  # Dictionary remains unchanged
        ]

        for input_text, expected_output in test_input:
            result = ProductValidator.sanitize_input(input_text)
            assert result == expected_output, f"Santitization failed: {input_text} -> {result}"
    

    def test_validate_registration_object_valid(self):
        valid_data = [
            {
                "name": "Test Product",
                "price": 29.99,
                "quantity": 10,
                "description": "A test product"
            },
            {
                "name": "PRODUCT UPPERCASE",  # Test case normalization
                "price": "49.50",  # String price
                "quantity": "5",   # String quantity
                "description": ""  # Empty description
            },
            {
                "name": "Minimal Product",
                "price": 0.01,  # Minimum price
                # quantity defaults to 0
                # description defaults to ""
            }
        ]

        for data in valid_data:
            is_valid, result = ProductValidator.validate_registration_object(data)
            assert is_valid == True, f"Valid data should pass: {data}"
            assert "product_name" in result
            assert "price" in result
            assert "quantity" in result
            assert "description" in result
            # Verify normalization
            if "name" in data:
                assert result["product_name"] == data["name"].strip().lower()


    def test_validate_registration_object_invalid(self):
        invalid_test_cases =  [
            # Missing name
            ({
                "price": 29.99
            }, "missing required field"),
            
            # Missing price
            ({
                "name": "Test Product"
            }, "missing required field: price"),
            
            # Invalid price
            ({
                "name": "Test Product",
                "price": -10.00
            }, "Price does not meet requirements"),
            
            # Invalid quantity
            ({
                "name": "Test Product",
                "price": 29.99,
                "quantity": -5
            }, "Invalid quantity"),
            
            # Invalid name
            ({
                "name": "",
                "price": 29.99
            }, "issing required field"),
            
            # Empty data
            ({}, "missing required field"),
            
            # Invalid data type
            ("not-a-dict", "input must be a dictionary"),
            (None, "input must be a dictionary"),
            ([], "input must be a dictionary"),
            (123, "input must be a dictionary")
        ]

        for data, expected_result in invalid_test_cases:
            is_valid, result = ProductValidator.validate_registration_object(data)
            assert is_valid == False, f"invalid data accepted:{data}"
            error_msg = str(result.get("error",result)).lower()
            assert expected_result.lower() in error_msg, f"Incorrect error message: {error_msg} for {data} "

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

