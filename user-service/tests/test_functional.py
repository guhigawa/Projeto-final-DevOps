"""Functional tests for user-service end-to-end for user-service"""
import pytest, requests, time, os

def get_service_port():
    if os.path.exists('/.dockerenv'):
        flask_port = os.getenv("FLASK_RUN_PORT")
        if flask_port:
            return flask_port
    
    dev_port = os.getenv("USER_SERVICE_PORT")
    if dev_port:
        return dev_port

    staging_port = os.getenv("STAGING_USER_PORT")
    if staging_port:
        return staging_port 
    
    return "3001"

PORT = get_service_port()
BASE_URL = f"http://localhost:{PORT}"

class TestUserServiceFunctional:
    def setup_method(self):
        self.base_url = BASE_URL
        self.client = requests.Session()
        self.client.timeout = 15  # seconds

        max_wait = 30 
        start_time = time.time()

        while time.time() - start_time < max_wait:
            try:
                response = requests.get(f"{self.base_url}/health", timeout=5)
                if response.status_code == 200:
                    print(f"User-service is healthy after {int(time.time() - start_time)}s")
                    
                    try:
                        requests_detailed = requests.get(f"{self.base_url}/health/detailed", timeout=5)
                        if requests_detailed.status_code == 200 and requests_detailed.json().get("status") == "healthy":
                            print("Detailed health check passed")
                            return
                    except:
                        print(f"deailed health check skipped")

                        return 
            
            except Exception as e:
                print(f"Service not ready yet: {e}")
            
            time.sleep(2)
        error_msg = f"Service at {self.base_url} not healthy after {max_wait}s"
        print(f"{error_msg}")
        pytest.skip(error_msg)

    def teardown_method(self):
        print(f"Test completed, cleaning up")
        self.client.close()


    def generate_unique_email(self):
        timestamp = int(time.time() * 1000) # multiply to get milliseconds
        return f"func_test_{timestamp}@example.com"


    def test_complete_user_lifecycle(self):

        email = self.generate_unique_email()
        valid_password = "StrongPass123!"
        print(f"Testing with email: {email}")

        # Register user
        register_response = requests.post(f"{BASE_URL}/register", json={
            "email":email,
            "password":valid_password}, timeout=10)
        
        print(f"Register response: {register_response.status_code}")
        assert register_response.status_code in [200,201], f"Registration failed: {register_response.text}"

        user_data = register_response.json()
        user_id = user_data.get("user_id") 
        assert user_id is not None, "User ID missing in registration response"

        #Login
        login_response = requests.post(f"{BASE_URL}/login", json={
            "email":email,
            "password":valid_password}, timeout=5)
        
        print(f"login response: {login_response.status_code}")
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"

        login_data = login_response.json()
        token = login_data.get('token')
        assert token is not None, "Token missing in login response"

        # Profile 
        headers = {"Authorization": f"Bearer {token}"}
        profile_response = requests.get(f"{BASE_URL}/profile", headers=headers, timeout=5)

        print(f"Profile response: {profile_response.status_code}")
        assert profile_response.status_code == 200, f"Profile fetch failed: {profile_response.text}"

        profile_data = profile_response.json()
        assert profile_data.get("email") == email, "Profile email does not match"
        assert profile_data.get("user_id") == user_id, "Profile user_id does not match"

        #profile update
        new_email = f"updated_{email}"
        update_response = requests.put(f"{BASE_URL}/profile", headers=headers, json={
            "email": new_email,}, timeout=5)
        
        print(f"Update response: {update_response.status_code}")
        assert update_response.status_code == 200, f"Profile update failed: {update_response.text}"

        # Verify update
        profile_response_after_update = requests.get(f"{BASE_URL}/profile", headers=headers, timeout=5)
        profile_data_after_update = profile_response_after_update.json()
        assert profile_response_after_update.status_code == 200, f"Profile fetch after update failed"
        assert profile_data_after_update.get("email") == new_email, "Update failed"

        # Logout
        logout_response = requests.post(f"{BASE_URL}/logout", headers=headers, timeout=5)
        print(f"Logout response: {logout_response.status_code}")
        assert logout_response.status_code == 200, f"Logout failed: {logout_response.text}"

        #Verify token invalidation after logout
        profile_response_after_logout = requests.get(f"{BASE_URL}/profile", headers=headers, timeout=5)
        print(f"Profile after logout response: {profile_response_after_logout.status_code}")
        assert profile_response_after_logout.status_code == 401, "Token should be invalid after logout"

        print("Functional user lifecycle test completed successfully")

    
    def test_registration_with_weak_password(self): 
        email = self.generate_unique_email()
        weak_passwords = ["short", #short password
                         "noupper123", #no uppercase letters
                         "NOLOWER123", #no lowercase letters
                         "NoNumber",   #no numbers
                         "",       #empty password
                         "  ",      #only spaces
                            "NoSpecial123", #no special characters
                         ]
        for i, weak_pass in enumerate(weak_passwords):
            email = f"weakpass_test_{i}_{int(time.time())}@example.com"
            
            registration_weak_passwords_response = requests.post(f"{BASE_URL}/register", json={
                "email": email,
                "password":weak_pass}, timeout=5)
            print(f"{weak_pass}, response status: {registration_weak_passwords_response.status_code}")
            assert registration_weak_passwords_response.status_code == 400, f"Weak password '{weak_pass}' should be rejected"

            error_data = registration_weak_passwords_response.json()
            error_msg = str(error_data.get("error", error_data)).lower()
            assert any (keyword in error_msg for keyword in ["must", "password", "characters", "least"])


    def test_registration_with_invalid_email(self):
        invalid_emails = ["plainaddress", #missing @
                          "@domain.com", #missing local part
                            "user@.com", #missing domain name
                            "user@domain.", #missing top-level domain
                            "", #empty email
                        ]
        for i, invalid_email in enumerate(invalid_emails):
            password = "ValidPass123!"
            invalid_email_response = requests.post(f"{BASE_URL}/register", json={
                "email": invalid_email,
                "password": password}, timeout=5)

            print(f"Testing invalid_email: '{invalid_email}', response status: {invalid_email_response.status_code}")
            assert invalid_email_response.status_code == 400, f"Invalid email '{invalid_email}' should be rejected"

            error_data = invalid_email_response.json()
            assert "error" in error_data, f"Error message missing for invalid email '{invalid_email}'" 
            assert "email" in error_data["error"].lower(), f"Unexpected error message for invalid email '{invalid_email}': {error_data['error']}"

    
    def test_rapid_registration_attempts(self):
        print("Testing rapid registration attempts to check rate limiting")

        base_email = f"ratelimit{int(time.time())}"
        successful_registrations = 0
        total_attempts = 5
        for i in range(total_attempts):
            email = f"{base_email}_{i}@example.com"
            
            try:
                rapid_registration_response = requests.post(f"{BASE_URL}/register", json={
                    "email": email,
                    "password":"ValidPass123!"}, timeout=5)
                
                if rapid_registration_response.status_code in [200,201]:
                    successful_registrations += 1
                    print(f"Attempt {i+1}: Registration succeeded")
            
            except Exception as e:
                print(f"Attempt {i+1}: Exception occurred: {str(e)}")
            
            time.sleep(1) 
        
        print(f"Total successful registrations out of {total_attempts} attempts: {successful_registrations}")
        assert successful_registrations > 0, "All rapid registration attempts failed, possible rate limiting issue"


if __name__ == "__main__":
    print("Starting functional tests for user-service")
    print(f"Using base URL: {BASE_URL}")

    try:
        health_response = requests.get(f"{BASE_URL}/health", timeout=5)
        if health_response.status_code == 200:
            print("User-service is healthy, proceeding with tests")
        else:
            print(f"User-service health check failed with status: {health_response.status_code}")

    except Exception as e:
        print(f"Not able to connect to user-service: {e}")
        print("Execute: docker-compose up user-service") 
