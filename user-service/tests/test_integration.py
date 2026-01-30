import pytest, requests, time, os;
from datetime import datetime


from helpers.test_helpers import TestHelpers
from helpers.evidence_logger import EvidenceLogger

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

#Connection test before running tests
print("Checking if User Service is up")
try:
    test_response = requests.get(f"http://localhost:{PORT}/health", timeout=10)
    print(f"Connection estabilished, status code: {test_response.status_code}")
    print(f"response: {test_response.text[:100]}") # First 100 characters of the response
except Exception as e:
    print(f"Failed to connect to User Service at {BASE_URL}: {str(e)}")
    print("Tests will fail")


@pytest.fixture 
def test_helpers():
    return TestHelpers(BASE_URL)


@pytest.fixture 
def evidence_logger():
    return EvidenceLogger("Integration Tests for User Service", BASE_URL)


@pytest.fixture 
def unique_email(test_helpers):
    return test_helpers.generate_unique_email()


@pytest.fixture(scope="function") 
def registered_user(test_helpers, unique_email):
    response, _ = test_helpers.register_user(email=unique_email)

    if response.status_code in [200,201,409]:
        return unique_email, response.json().get('user_id')
    else:
        pytest.fail(f"User registration failed: {response.status_code}")


@pytest.fixture(scope="function") 
def authenticated_user(test_helpers, registered_user):
    email, user_id = registered_user
    login_response = test_helpers.login_user(email=email)

    if login_response.status_code == 200:
        token = login_response.json().get('token')
        return email, user_id, token
    else:
        pytest.fail(f"User login failed: {login_response.status_code}")


#Defining the test class for user service
class TestUserService:
    def setup_method(self):
        self.base_url = BASE_URL
        self.client = requests.Session()
        self.client.timeout = 10  # seconds

        time.sleep(3)  # brief pause to avoid overwhelming the service

    def test_health_check_detailed(self, evidence_logger):
        test_name = "Detailed Health Check"
        try: 
            response =requests.get(f"{BASE_URL}/health/detailed")
            data = response.json()
            expected_status_code = 200
            #Validating API and DB status
            success = (response.status_code == expected_status_code and
                       data.get('status') == 'healthy' and
                       data.get('checks', {}).get('database_connection') == True and
                       data.get('checks', {}).get('database_query') == True
                       )
            details = f"Status: {data.get('status')}, DB Connection: {data.get('checks', {}).get('database_connection')}, DB Query: {data.get('checks', {}).get('database_query')}"
             
            evidence_logger.log_test_result(test_name, success, details, data)
            assert success, f"Expected status code {expected_status_code} but got {response.status_code}"
        
        except Exception as e:
            evidence_logger.log_test_result(test_name, False, f"Exception occurred: {str(e)}")
            pytest.fail(f"Test failed due to exception: {str(e)}")
    

    def test_health_check_simple(self, evidence_logger):
        test_name = "Simple health check"
        try:
            response = requests.get(f"{BASE_URL}/health")
            success = response.status_code == 200

            details = f"Status code:{response.status_code}"
            evidence_logger.log_test_result(test_name, success, details, response.json())
            assert success

        except Exception as e:
            evidence_logger.log_test_result(test_name, False, f"Exception occurred: {str(e)}")
            pytest.fail(f"Test failed:{str(e)}")
        
    
class TestUserServiceAuthentication:


    def test_user_registration(self, test_helpers, evidence_logger, unique_email):
        test_name = "User registration test"
        try:
            response,_ = test_helpers.register_user(email=unique_email)
            data = response.json()

            correct_status = response.status_code in [200,201] #200 for successful response, 201 for resource created
            has_user_id = 'user_id' in data
            has_email = data.get('email') == unique_email

            success = correct_status and has_user_id and has_email

            
            details = f"Email: {unique_email}, Status Code: {response.status_code}, User ID: {data.get('user_id')}"
            evidence_logger.log_test_result(test_name, success, details, data)
            assert success, f"Registration failed{details}"
        
        except Exception as e:
            evidence_logger.log_test_result(test_name, False, f"Exception occurred: {str(e)}")
            pytest.fail(f"Test failed due to exception: {str(e)}")


    def test_duplicate_user_registration(self, test_helpers, evidence_logger, unique_email):
        test_name = "Duplicate User Registration Test"
        try:

            response1, _ = test_helpers.register_user(email=unique_email) #only the response is needed from the method self.register_user in test_helpers.py
            response2, _ = test_helpers.register_user(email=unique_email)

            success = response2.status_code == 409  #409 Conflict for duplicate registration

            details = f"First Registration Status: {response1.status_code}, Second Registration Status: {response2.status_code}"
            evidence_logger.log_test_result(test_name, success, details, response2.json())
            assert success
        
        except Exception as e:
            evidence_logger.log_test_result(test_name, False, f"Exception occurred: {str(e)}")
            pytest.fail(f"Test failed due to exception: {str(e)}")

    
    def test_user_login(self, test_helpers, evidence_logger, registered_user):
        test_name = "User Login Test"
        try:
            email,_= registered_user
            login_response = test_helpers.login_user(email=email)
            data = login_response.json()

            status = login_response.status_code == 200
            has_token = 'token' in data
            has_user_id = 'user_id' in data
            success = status and has_token and has_user_id
            
            details = f"Email: {email}, Status Code: {login_response.status_code}, User ID: {data.get('user_id')}"
            evidence_logger.log_test_result(test_name, success, details, data)
            assert success, f"Login failed: {details}"

        except Exception as e:
            evidence_logger.log_test_result(test_name, False, f"Exception occurred: {str(e)}")
            pytest.fail(f"Test failed due to exception: {str(e)}")
    

    def test_user_login_wrong_password(self, test_helpers, evidence_logger, registered_user):
        test_name = "Login with wrong password"
        try:
            email, _ = registered_user

            login_response = test_helpers.login_user(email=email, password="Wrongpassword@123")

            success = login_response.status_code == 401
            details = f"Expected 401, got {login_response.status_code}"
            evidence_logger.log_test_result(test_name, success, details, login_response.json())
            assert success
        
        except Exception as e:
            evidence_logger.log_test_result(test_name,False, details, f"Exception:{str(e)}")
            pytest.fail(f"Test failed: {str(e)}")


class TestUserServiceProfile:


    def test_update_profile(self, evidence_logger,authenticated_user):
        test_name = "Update User Profile Test"

        try:
            email, _,token = authenticated_user  
            new_test_user = "update" + email

            print(f"actual email: {email}")
            print(f"new email: {new_test_user}")
            
            update_response = requests.put(f"{BASE_URL}/profile", headers={"Authorization": f"Bearer {token}"}, json={"email": new_test_user})

            update_success = update_response.status_code == 200
            print("Update profile response status code:", update_response.status_code)

            if update_success:
                profile_response = requests.get(f"{BASE_URL}/profile", headers={"Authorization": f"Bearer {token}"})
                
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    actual_email = profile_data.get('email')
                    print(f"email in profile: {actual_email}")
                    print(f"expected email: {profile_response.json().get('email')}")
            
                    email_updated = actual_email == new_test_user

                    success = update_success and email_updated
                    details = f"Status Code: {update_response.status_code}, New Email: {new_test_user}, Email in Profile: {actual_email}"
                    evidence_logger.log_test_result(test_name, success, details, {
                        "update_response": update_response.json(),
                        "profile_data": profile_data
                        })
                    assert success, f"Profile update failed: {details}"

                else:
                # Profile GET request failed   
                    details = f"Update succeeded ({update_response.status_code}) but GET profile failed: {profile_response.status_code}"
                    evidence_logger.log_test_result(test_name, False, details, {
                        "update_response": update_response.json(),
                        "profile_error": f"GET failed with status {profile_response.status_code}"
                        })
                    pytest.fail(details)
            else:
                # Profile update failed
                details = f"Profile update failed with status: {update_response.status_code}"
                evidence_logger.log_test_result(test_name, False, details, update_response.json())  
                pytest.fail(details) 
                
        except Exception as e:
            evidence_logger.log_test_result(test_name, False, f"Exception occurred: {str(e)}")
            pytest.fail(f"Test failed due to exception: {str(e)}")


    def test_get_user_by_id(self, evidence_logger, authenticated_user): 
        test_name = "Get User by ID Test"
        try:
            email, user_id, token = authenticated_user

            response = requests.get(
                f"{BASE_URL}/users/{user_id}",
                headers={"Authorization": f"Bearer {token}"}
            )

            success = response.status_code == 200
            if success:
                data = response.json()
                success = data.get('user_id') == user_id and data.get('email') == email
            
            details = f"Status: {response.status_code}, User ID: {user_id}"
            evidence_logger.log_test_result(test_name, success, details, response.json())
            assert success
        
        except Exception as e:
            evidence_logger.log_test_result(test_name, False, f"Exception: {str(e)}")
            pytest.fail(f"Test failed: {str(e)}")


    def test_user_profile_and_logout(self, evidence_logger, authenticated_user):
        test_name = "User Logout and profile Test"
        try:
            email, user_id, token = authenticated_user

            profile_before_logout = requests.get(f"{BASE_URL}/profile", headers={"Authorization": f"Bearer {token}"})
            logout_response = requests.post(f"{BASE_URL}/logout", headers={"Authorization": f"Bearer {token}"})
            profile_after_logout = requests.get(f"{BASE_URL}/profile", headers={"Authorization": f"Bearer {token}"})
            data = {
                "profile_before_logout": profile_before_logout.json() if profile_before_logout.status_code == 200 else {"error": "Failed to fetch profile"},
                "logout_response": logout_response.json() if logout_response.status_code == 200 else {"error": "Failed to logout"},
                "profile_after_logout": profile_after_logout.json() if profile_after_logout.status_code == 200 else {"error": "Unauthorized access"}
            }

            success = (profile_before_logout.status_code == 200 and
                       logout_response.status_code == 200 and
                       profile_after_logout.status_code == 401)
            details = f"Profile Before Logout Status: {profile_before_logout.status_code}, Logout Status: {logout_response.status_code}, Profile After Logout Status: {profile_after_logout.status_code}"
            evidence_logger.log_test_result(test_name, success, details, data)
            assert success, f"Test failed: {details}"
        
        except Exception as e:
            evidence_logger.log_test_result(test_name, False, f"Exception occurred: {str(e)}")
            pytest.fail(f"Test failed due to exception: {str(e)}")


class TestUserServiceSecurity:


    def test_registration_weak_password(self, test_helpers, evidence_logger):
        test_name = "Registration with weak password"
        try:
            email = test_helpers.generate_unique_email()

            response, _ = test_helpers.register_user(
                email = email,
                password = "weak"
            )

            success = response.status_code == 400
            details = f"Expected code 400 for weak password, got {response.status_code}"
            evidence_logger.log_test_result(test_name, success, details, response.json())
            assert success
    
        except Exception as e:
            evidence_logger.log_test_result(test_name, False, f"Exception: {str(e)}")
            pytest.fail(f"Test failed: {str(e)}")
    

    def test_registration_invalid_email(self, test_helpers, evidence_logger):
        test_name = "Registration with invalid email"

        try:
            response,_ = test_helpers.register_user(
                email = "invalid-email",
                password = "StrongPass@123"
            )

            success = response.status_code == 400
            details = f"Expected code 400 for invalid email, got {response.status_code}"

            evidence_logger.log_test_result(test_name, success, details, response.json())
            assert success
        
        except Exception as e:
            evidence_logger.log_test_result(test_name, False, f"Exception: {str(e)}")
            pytest.fail(f"Test failed: {str(e)}")

                
