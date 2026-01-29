import re

class ProductValidator:
    #REGEX for simpler product name validation
    PRODUCT_REGEX = r'^[a-zA-Z0-9\s\-\'\.\,\(\)]+$'

    #quantity configuration
    MIN_QUANTITY = 0
    MAX_QUANTITY = 9999

    #Price configuration
    MIN_PRICE = 0.00
    MAX_PRICE = 9999.99

    #description configuration
    MAX_DESCRIPTION = 2000

    @staticmethod
    def validate_product(name):
        if not isinstance(name, str):
            return False, "Product name must be a valid string"
        
        product_to_validate = name.strip()

        if len(product_to_validate) == 0:
            return False, "Product name cannot be empty"
        
        if len(product_to_validate) > 254:
            return False, "Product name too long (max 254 characters)"

        #validating product name format with REGEX
        if not re.match(ProductValidator.PRODUCT_REGEX, product_to_validate):
            return False, "Invalid product name format.Only letters, numbers, spaces, and - ' . , ( ) are allowed"
        
        return True, product_to_validate.lower()
    
    @staticmethod
    def validate_product_quantity(quantity):
        try:
            if quantity is None or quantity == "":
                quantity_to_validate = 0
                return True,quantity_to_validate

            if isinstance(quantity,float):
                return False, "Quantity must be a valid integer"

            if isinstance(quantity, str):
                quantity_to_validate = int(quantity.strip())
            else:
                quantity_to_validate = int(quantity)
            
            if quantity_to_validate < ProductValidator.MIN_QUANTITY:
                return False, f"Quantity must be at least {ProductValidator.MIN_QUANTITY}"
            
            if quantity_to_validate > ProductValidator.MAX_QUANTITY:
                return False, f"Quantity must be lower than {ProductValidator.MAX_QUANTITY}"
            
            return True, quantity_to_validate
        
        except (ValueError, TypeError):
            return False, "Quantity must be a valid integer"
    
    @staticmethod
    def validate_product_price(price):
        try:
            if isinstance(price,str):
                price_to_validate = float(price.strip())
            else:
                price_to_validate = float(price)
            
            if price_to_validate < ProductValidator.MIN_PRICE:
                return False, f"Price must be at least {ProductValidator.MIN_PRICE}"

            if price_to_validate > ProductValidator.MAX_PRICE:
                return False, f"Price must be lower than {ProductValidator.MAX_PRICE}"
            
            price_to_validate = round(price_to_validate,2)
            return True, price_to_validate

        except (ValueError, TypeError):
            return False, "Price must be a valid number"
    
    @staticmethod
    def validate_product_description(description):
        if description is None:
            return True, ""
        
        if not isinstance(description,str):
            return False, "Description must be a string"
        
        description_to_validate = description.strip()

        if len(description_to_validate) > ProductValidator.MAX_DESCRIPTION:
            return False, f"Description too long - maximum characters:{ProductValidator.MAX_DESCRIPTION}"

        return True, description_to_validate


    @staticmethod
    def sanitize_input(text):
        """Removal of potential dangerous characters from input text"""

        if not isinstance(text, str):
            return text
        
        dangerous_characters = ['<', '>', '"', "'", ';', '/', '\\','='] 
        for char in dangerous_characters:
            text = text.replace(char, '')
        
        return text.strip()
    

    @staticmethod
    def validate_registration_object(data):
        if not isinstance(data, dict):
            return False, {"error":"input must be a dictionary"}
        
        required_fields = ['name', 'price']

        for field in required_fields:
            if field not in data or data[field] is None:
                return False, {"error": f"missing required field: {field}"}
        
        #Validate name
        name = data['name']
        is_valid_name, name_result = ProductValidator.validate_product(name)
        if not is_valid_name:
            return False, {"error": f"missing required field: {name_result}"}

        #Validate price
        price = data['price']
        is_valid_price, price_result = ProductValidator.validate_product_price(price)
        if not is_valid_price:
            return False, {
                "error": "price does not meet requirements",
                "requirements": {
                    "min_price": ProductValidator.MIN_PRICE,
                    "max_price": ProductValidator.MAX_PRICE,
                    "errors": price_result
                }
            }

        #Validate quantity
        quantity = data.get('quantity',0 ) #Because it is an optional field get is more appropriate as it allows to put de default value if the field is not sent and wont break the code
        is_valid_quantity, quantity_result = ProductValidator.validate_product_quantity(quantity)
        if not is_valid_quantity:
            return False, {"error": f"Invalid quantity: {quantity_result}"}
        
        #Validate description
        description = data.get('description', '')
        if description and not isinstance(description,str):
            return False, {"error": "Description must be a string"}
        
        sanitized_name = ProductValidator.sanitize_input(name).strip().lower()
        sanitized_description = ProductValidator.sanitize_input(description).strip().lower()


        return True, {
            "product_name": sanitized_name,
            "price": price_result,  
            "quantity": quantity_result,  
            "description": sanitized_description
        }