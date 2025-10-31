import requests, json, time

class TestHelpers:
    __test__ = False  # Prevent pytest from collecting this class as a test case

    def __init__(self, base_url):
        self.base_url = base_url


    def generate_unique_email(self):
        timestamp = int(time.time())
        return f"test_{timestamp}@example.com"
    
    def register_user(self, email=None, password="Test@1234"):
        if email is None:
            email = self.generate_unique_email()
            
        user_data = {
            "email": email,
            "password": password
        }
        response = requests.post(f"{self.base_url}/register", json=user_data)
        return response, user_data
    
    
    def login_user(self, email,password="Test@1234"):
        payload = {
            "email": email,
            "password": password
        }
        response = requests.post(f"{self.base_url}/login", json=payload)
        return response
    

    def get_user_token(self, email, password="Test@1234"):
        
        register_response, _ = self.register_user(email, password)
        if register_response.status_code != 200:
            return None
        
        login_response = self.login_user(email, password)
        if login_response.status_code == 200:
            return login_response.json().get('token')
        return None


    
