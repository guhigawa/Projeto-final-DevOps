import requests, random, time

class ProductAuthHelpers:
    user_url = "http://localhost:3001"
    def __init__(self, user_service_url=user_url):
        self.user_service_url = user_service_url

    
    def create_test_user(self):
        email = f"product_test{int(time.time())}@example.com"

        register_response = requests.post(f"{self.user_service_url}/register", json={"email":email,"password":"product123"})
        login_response = requests.post(f"{self.user_service_url}/login",json={"email":email,"password":"product123"})

        if login_response.status_code == 200:
            login_data = login_response.json()
            return{
                "email":email,
                "token":login_data.get("token"),
                "user_id":login_data.get("user_id"),
                "headers":{"Authorization": f"Bearer {login_data.get('token')}"}
            }
        else:
            raise Exception(f"Fail to create user{login_response.text}")