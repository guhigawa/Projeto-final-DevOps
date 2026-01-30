import requests, os, time, uuid

class ProductAuthHelpers:
    
    def __init__(self):
        self.user_service_url = os.getenv("USER_SERVICE_URL","http://localhost:3001")

    
    def create_test_user(self):
        unique_id = uuid.uuid4().hex[:8]
        email = f"product_test{unique_id}@example.com" 

        register_response = requests.post(f"{self.user_service_url}/register", json={"email":email,"password":"Product@123"})

        time.sleep(0.5) # Pause to avoid race conditions

        login_response = requests.post(f"{self.user_service_url}/login",json={"email":email,"password":"Product@123"})

        if login_response.status_code == 200:
            login_data = login_response.json()
            return{
                "email":email,
                "token":login_data.get("token"),
                "user_id":login_data.get("user_id"),
                "headers":{"Authorization": f"Bearer {login_data.get('token')}"}
            }
        else:
            time.sleep(0.5)
            login_response = requests.post(f"{self.user_service_url}/login",json={"email":email,"password":"Product@123"})
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