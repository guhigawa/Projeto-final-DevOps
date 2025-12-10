import pytest, requests, os

from product_test_helpers.auth_helpers import ProductAuthHelpers
from product_test_helpers.product_tester_helpers import TestProductHelpers
from product_test_helpers.product_evidence_logger import ProductEvidenceLogger

#debug for actions

#Verification of all possivle variables
print("Environment Variables:")
print(f"FLASK_RUN_PORT: {os.getenv('FLASK_RUN_PORT')}")
print(f"STAGING_PRODUCT_PORT: {os.getenv('STAGING_PRODUCT_PORT')}")
print(f"PRODUCT_SERVICE_PORT: {os.getenv('PRODUCT_SERVICE_PORT')}")
print(f"Inside Docker container? {os.path.exists('/.dockerenv')}")

def get_service_port():
    if os.path.exists('/.dockerenv'):
        flask_port = os.getenv("FLASK_RUN_PORT")
        if flask_port:
            print(f"Using FLASK_RUN_PORT:{flask_port}")
            return flask_port
        else:
            print("FLASK_RUN_PORT not set")
    else:
        print("Running outside the container")

    staging_port = os.getenv("STAGING_PRODUCT_PORT")
    if staging_port:
        print(f"Using STAGING_PRODUCT_PORT: {staging_port}")
        return staging_port
    
    dev_port = os.getenv("PRODUCT_SERVICE_PORT")
    if dev_port:
        print(f"Using PRODUCT_SERVICE_PORT: {dev_port}")
        return dev_port
    
    
    print("Using default port: 3002")
    return "3002"

PORT = get_service_port()
BASE_URL = f"http://localhost:{PORT}"

#Connection test before running tests
print("Checking if Product Service is up")
try:
    test_response = requests.get(f"http://localhost:{PORT}/health", timeout=10)
    print(f"Connection estabilished, status code: {test_response.status_code}")
    print(f"response: {test_response.text[:100]}") # First 100 characters of the response
except Exception as e:
    print(f"Failed to connect to Product Service at {BASE_URL}: {str(e)}")
    print("Tests will fail")

@pytest.fixture
def product_test_helpers():
    return TestProductHelpers(BASE_URL)


@pytest.fixture(scope="session")
def product_test_auth_helpers():
    return ProductAuthHelpers()


@pytest.fixture
def product_evidence_logger():
    return ProductEvidenceLogger("Integration Tests for Product Service",BASE_URL)


@pytest.fixture(scope="session")
def authenticated_user(product_test_auth_helpers):
    return product_test_auth_helpers.create_test_user()


@pytest.fixture
def generate_item(product_test_helpers):
    return product_test_helpers.generate_unique_object()


@pytest.fixture
def create_test_user(product_test_auth_helpers):
    return product_test_auth_helpers.create_test_user()


class TestProductService:
    def test_health_check_detailed(self, product_evidence_logger):
        test_name = "Detailed Health Check | Product Service"
        
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
             
            product_evidence_logger.log_test_result(test_name, success, details, data)
            assert success, f"Expected status code {expected_status_code} but got {response.status_code}"
            
        
        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception occurred: {str(e)}")
            pytest.fail(f"Test failed due to exception: {str(e)}")
    

    def test_create_user_test(self, product_test_auth_helpers, product_evidence_logger):
        test_name = "Registration and login of test user for product test"
        
        try:
            user_data_response = product_test_auth_helpers.create_test_user()
                        
            has_token = 'token' in user_data_response
            has_user_id = 'user_id' in user_data_response
            test_email = 'email' in user_data_response

            success = has_token and has_user_id and test_email

            details = f"Email:{test_email}, User test ID:{user_data_response.get('user_id')}"
            product_evidence_logger.log_test_result(test_name, success, details, user_data_response)
            assert success, f"Regsitration and login failed{details}"

        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception ccurred: {str(e)}")
            pytest.fail(f"Test failed due to exception: {str(e)}")


    def test_create_item(self, authenticated_user, generate_item, product_evidence_logger):
        test_name = "Create product item"

        try:
            headers = authenticated_user["headers"]
            product_data = generate_item
            post_response = requests.post(f"{BASE_URL}/products", headers=headers, json=product_data)
        
            success = post_response.status_code == 201
            response_data = post_response.json() if success else {}
                        
            details = f"Status:{post_response.status_code}, Product:{product_data['name']}, User:{authenticated_user['email']}"
            product_evidence_logger.log_test_result(test_name,success, details, response_data)
            assert success,f"Item creation failed:{details}"
        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception ccurred: {str(e)}")
            pytest.fail(f"Test failed due to exception: {str(e)}")
    

    def test_get_items(self, authenticated_user, generate_item, product_evidence_logger):
        test_name = "Get user item list"

        try:
            headers = authenticated_user["headers"]
            
            product_data = generate_item
            post_response = requests.post(f"{BASE_URL}/products", headers=headers, json=product_data)

            if post_response.status_code == 201:
                product_id = post_response.json().get("id")
            else:
                pytest.fail("Failed to create test product for get_items test")
            
            get_response = requests.get(f"{BASE_URL}/products", headers=headers)
            response_data = get_response.json()
            products = response_data.get("products",[])

            success = get_response.status_code == 200
            product_found = any(p["id"] == product_id for p in products)

            details = f"Status: {get_response.status_code}, Products found: {len(products)}, Target product found: {product_found}"
            product_evidence_logger.log_test_result(test_name,success, details, response_data)
            assert success and product_data, f"Get items failed:{details}"
        
        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception occurred: {str(e)}")
            pytest.fail(f"Test failed due to exception: {str(e)}")
    

    def test_update_item(self, authenticated_user, generate_item, product_evidence_logger):
        test_name = "Update user item list"

        try:
            headers = authenticated_user["headers"]

            product_data = generate_item
            print(f"DEBUG:Creating product with data:{product_data}")

            post_response = requests.post(f"{BASE_URL}/products", headers=headers, json=product_data)
            print(f"DEBUG: POST response status: {post_response.status_code}")
            print(f"DEBUG: POST response body: {post_response.text}")

            if post_response.status_code == 201:
                post_data = post_response.json()
                print(f"DEBUG: POST response JSON keys: {post_data.keys()}")
                product_id = post_response.json().get("id")
                print(f"DEBUG: Extracted product_id: {product_id}")
            else:
                pytest.fail(f"Failed to create test product for get_items test{post_response.status_code} - {post_response.text}")
            
            update_payload = {
                "id": product_id,
                "name": "updated_name_test",
                "price": 199.99,
                "description": "Update_test description",
                "quantity":3
            }
            print(f"DEBUG: Update payload: {update_payload}")

            put_response = requests.put(f"{BASE_URL}/products", headers=headers, json=update_payload)
            print(f"DEBUG: PUT response status: {put_response.status_code}")
            print(f"DEBUG: PUT response body: {put_response.text}")
            success = put_response.status_code == 200
            response_data = put_response.json() if success else {}
            

            if success:
                get_response = requests.get(f"{BASE_URL}/products", headers=headers)
                products = get_response.json().get("products", [])
                updated_product = next((p for p in products if p["id"] == product_id), None)

                if updated_product:
                    name_updated = updated_product["name"] == "updated_name_test"
                    price_updated = updated_product["price"] == 199.99
                    success = success and name_updated and price_updated
            
            details = f"Product ID: {product_id}, Update status: {put_response.status_code}"
            product_evidence_logger.log_test_result(test_name, success, details, response_data)
            assert success, f"Update failed: {details}"
            
        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception occurred: {str(e)}")
            pytest.fail(f"Test failed due to exception: {str(e)}")


    def test_delete_item(self, authenticated_user, generate_item, product_evidence_logger):
        test_name = "Delete product item"
        try:
            headers = authenticated_user["headers"]
                        
            product_data = generate_item
            post_response = requests.post(f"{BASE_URL}/products", headers=headers, json=product_data)
            
            if post_response.status_code == 201:
                product_id = post_response.json().get("id")
            else:
                pytest.fail("Failed to create test product for get_items test")
            
            product_id = post_response.json().get("id")
            
            delete_response = requests.delete(f"{BASE_URL}/products", headers=headers, json={"id": product_id})
            success = delete_response.status_code == 200
            
            if success:
                get_response = requests.get(f"{BASE_URL}/products", headers=headers)
                products = get_response.json().get("products", [])
                product_still_exists = any(p["id"] == product_id for p in products)
                success = success and not product_still_exists
            
            details = f"Product ID: {product_id}, Delete status: {delete_response.status_code}"
            product_evidence_logger.log_test_result(test_name, success, details, delete_response.json() if success else {})
            assert success, f"Delete failed: {details}"
            
        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception occurred: {str(e)}")
            pytest.fail(f"Test failed due to exception: {str(e)}")
