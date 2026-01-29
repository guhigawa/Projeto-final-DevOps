import re


class Validators:

    # Regex simple email validation
    EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    # Password configuration
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 20

    @staticmethod
    def validate_email(email):
        if not email or not isinstance(email, str): 
            return False, "Email must be a valid string" #tuple unpacking - 2 values returned boolean and message
        
        email_to_validate = email.strip() #removing leading and trailing spaces 
        
        # Validating email format with regex
        if not re.match(Validators.EMAIL_REGEX, email_to_validate):
            return False, "Invalid email format"
    
        # Verifying email length
        if len(email_to_validate) > 254: # RFC 5331 limit
            return False, "Email is too long"
        
        return True, email_to_validate.lower() 
    
    @staticmethod
    def validate_password(password):
        if not password or not isinstance(password, str): # Not possible to use in list, because if it is None it is not possible to use len(errors)
            return False, ["Password must be a valid string"]
        
        errors = []
        special_characters = "@#/-_&!"

        if len(password) < Validators.MIN_PASSWORD_LENGTH:
            errors.append(f"password must be at least {Validators.MIN_PASSWORD_LENGTH} characters long")

        if len(password) > Validators.MAX_PASSWORD_LENGTH:
            errors.append(f"password must be at most {Validators.MAX_PASSWORD_LENGTH} characters long")
        
        if not any(char.isupper() for char in password):
            errors.append("password must contain at least one uppercase letter")

        if not any(char.islower() for char in password):
            errors.append("password must contain at least one lowercase letter")
        
        if not any(char.isdigit() for char in password):
            errors.append("password must contain at least one number")
        
        if not any(char in special_characters for char in password):
            errors.append(f"password must contain at least one special character: {special_characters}")
        
        return len(errors) == 0, errors # len(errors) == 0 returns True if no errors were found
    
    @staticmethod
    def sanitize_input(text):
        """Removal of potential dangerous characters from input text"""

        if not isinstance(text, str): # Condition to guarantee that only string types goes throguh sanitization
            return text
        
        dangerous_characters = ['<', '>', '"', "'", ';', '/', '\\','='] 
        for char in dangerous_characters:
            text = text.replace(char, '')
        
        return text.strip()
    
    @staticmethod
    def validate_registration_data(data):
        if not isinstance(data, dict):
            return False, {"error":"input must be a dictionary"}
        
        required_fields = ['email', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                return False, {"error": f"missing required field: {field}"}    

        email = data['email']
        is_valid_email, email_result = Validators.validate_email(email)
        if not is_valid_email:
            return False, {"error": f"invalid email: {email_result}"}

        password = data['password']
        is_valid_password, password_result = Validators.validate_password(password)
        if not is_valid_password:
            return False,  {
                "error": "password does not meet requirements",
                "requirements": {
                    "min_length": Validators.MIN_PASSWORD_LENGTH,
                    "max_length": Validators.MAX_PASSWORD_LENGTH,
                    "special characters": "@#/-_&!",
                    "errors": password_result
                }
            }
        

        return True, {
            "email": Validators.sanitize_input(data['email'].strip().lower()),
            "password": data['password']  # Passwords should not be altered to not affect hashing
        }