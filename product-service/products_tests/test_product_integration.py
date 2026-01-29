import pytest, requests, os

from product_test_helpers.auth_helpers import ProductAuthHelpers
from product_test_helpers.product_tester_helpers import TestProductHelpers
from product_test_helpers.product_evidence_logger import ProductEvidenceLogger

#debug for actions

#Verification of all possible variables
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
    
    dev_port = os.getenv("PRODUCT_SERVICE_PORT")
    if dev_port:
        print(f"Using PRODUCT_SERVICE_PORT: {dev_port}")
        return dev_port

    staging_port = os.getenv("STAGING_PRODUCT_PORT")
    if staging_port:
        print(f"Using STAGING_PRODUCT_PORT: {staging_port}")
        return staging_port  
    
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


class TestProductServiceHealth:
    def test_health_check_simple(self, product_evidence_logger):
        test_name = "Simple Health Check | Product Service"
        
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=10)
            success = response.status_code == 200
            
            details = f"Status code: {response.status_code}"
            product_evidence_logger.log_test_result(test_name, success, details, response.json())
            assert success, f"Expected 200, got {response.status_code}"
            
        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception occurred: {str(e)}")
            pytest.fail(f"Test failed: {str(e)}")


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
    

class TestProductServiceAuthentication:
    def test_create_user_test(self, product_test_auth_helpers, product_evidence_logger):
        test_name = "Registration and login of test user for product test"
        
        try:
            user_data_response = product_test_auth_helpers.create_test_user()
                        
            has_token = 'token' in user_data_response
            has_user_id = 'user_id' in user_data_response
            test_email = 'email' in user_data_response

            success = has_token and has_user_id and test_email

            details = f"Email:{user_data_response.get('email')}, User test ID:{user_data_response.get('user_id')}"
            product_evidence_logger.log_test_result(test_name, success, details, user_data_response)
            assert success, f"Registration and login failed{details}"

        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception ccurred: {str(e)}")
            pytest.fail(f"Test failed due to exception: {str(e)}")

    
    def test_create_product_withouth_auth(self, generate_item, product_evidence_logger):
        test_name = "Create Product without Authentication"

        try:
            product_data = generate_item
            
            response = requests.post(f"{BASE_URL}/products", json=product_data, timeout=10)
            success = response.status_code == 401
            
            details = f"Expected 401 without token, got {response.status_code}"
            product_evidence_logger.log_test_result(test_name, success, details,response.json() if response.text else {})
            assert success, f"Should require authentication: {details}"
            
        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception: {str(e)}")
            pytest.fail(f"Test failed: {str(e)}")

    def test_get_products_without_auth(self, product_evidence_logger):
        test_name = "Get Products without Authentication"
        
        try:
            response = requests.get(f"{BASE_URL}/products", timeout=10)
            success = response.status_code == 401
            
            details = f"Expected 401 without token, got {response.status_code}"
            product_evidence_logger.log_test_result(test_name, success, details,response.json() if response.text else {})
            assert success, f"Should require authentication: {details}"
            
        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception: {str(e)}")
            pytest.fail(f"Test failed: {str(e)}")
    

    def test_update_product_without_auth(self, product_evidence_logger):
        test_name = "Update Product without Authentication"
        
        try:
            update_data = {
                "id": 1,
                "name": "Updated Product"
            }
            
            response = requests.put(f"{BASE_URL}/products", json=update_data, timeout=10)
            success = response.status_code == 401
            
            details = f"Expected 401 without token, got {response.status_code}"
            product_evidence_logger.log_test_result(test_name, success, details,response.json() if response.text else {})
            assert success, f"Should require authentication: {details}"
            
        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception: {str(e)}")
            pytest.fail(f"Test failed: {str(e)}")


class TestProductServiceCRUD:
    def test_create_item(self, authenticated_user, generate_item, product_evidence_logger):
        test_name = "Create product item"

        try:
            headers = authenticated_user["headers"]
            product_data = generate_item

            print(f"DEBUG: Product data: {product_data}")
            post_response = requests.post(f"{BASE_URL}/products", headers=headers, json=product_data)
            print(f"DEBUG: Response status: {post_response.status_code}")  # ← Adicionar
            print(f"DEBUG: Response body: {post_response.text}") 
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
                pytest.fail(f"Failed to create test product for get_items test: {post_response.status_code} - {post_response.text}")
            
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
            post_response = requests.post(f"{BASE_URL}/products", headers=headers, json=product_data)

            if post_response.status_code == 201:
                product_id = post_response.json().get("id")
            else:
                pytest.fail(f"Failed to create test product for get_items test: {post_response.status_code} - {post_response.text}")
            
            update_payload = {
                "id": product_id,
                "name": "updated-name-test",
                "price": 199.99,
                "description": "Update test description",
                "quantity":3
            }

            put_response = requests.put(f"{BASE_URL}/products", headers=headers, json=update_payload)
            success = put_response.status_code == 200
            response_data = put_response.json() if success else {}
            

            if success:
                get_response = requests.get(f"{BASE_URL}/products", headers=headers)
                products = get_response.json().get("products", [])
                updated_product = next((p for p in products if p["id"] == product_id), None)

                if updated_product:
                    name_updated = updated_product["name"] == "updated-name-test"
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


class TestProductServiceValidation:
    def test_create_product_invalid_name(self, authenticated_user, product_evidence_logger):
        test_name = "Create product with invalid data"

        try:
            headers = authenticated_user["headers"]
            invalid_data = {
                "name": "", #empty name
                "price": 29.99,
                "quantity":10
            }

            post_response = requests.post(f"{BASE_URL}/products", headers=headers, json=invalid_data, timeout=10)
            success = post_response.status_code == 400
            details = f"Expected 400 for empty name, got {post_response.status_code}"
            product_evidence_logger.log_test_result(test_name, success, details, post_response.json() if post_response.text else {})
            assert success, f"Should reject empty product name: {details}"
        
        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception: {str(e)}")
            pytest.fail(f"Test failed: {str(e)}")
    

    def test_create_product_invalid_price(self, authenticated_user, product_evidence_logger):
        test_name = "Create product with invalid price"

        try:
            headers = authenticated_user["headers"]
            invalid_data = {
                "name": "Invalid Price Product",
                "price": -10.00, #negative price
                "quantity":5
            }

            post_response = requests.post(f"{BASE_URL}/products", headers=headers, json=invalid_data, timeout=10)
            success = post_response.status_code == 400
            details = f"Expected 400 for negative price, got {post_response.status_code}"
            product_evidence_logger.log_test_result(test_name, success, details, post_response.json() if post_response.text else {})
            assert success, f"Should reject negative price: {details}"
        
        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception: {str(e)}")
            pytest.fail(f"Test failed: {str(e)}")
    

    def test_create_product_invalid_quantity(self, authenticated_user, product_evidence_logger):
        test_name = "Create product with invalid quantity"

        try:
            headers = authenticated_user["headers"]
            invalid_data = {
                "name": "Invalid Quantity Product",
                "price": 19.99,
                "quantity": -5 #negative quantity
            }

            post_response = requests.post(f"{BASE_URL}/products", headers=headers, json=invalid_data, timeout=10)
            success = post_response.status_code == 400
            details = f"Expected 400 for negative quantity, got {post_response.status_code}"
            product_evidence_logger.log_test_result(test_name, success, details, post_response.json() if post_response.text else {})
            assert success, f"Should reject negative quantity: {details}"
        
        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception: {str(e)}")
            pytest.fail(f"Test failed: {str(e)}")
    

    def test_create_product_missing_required_fields(self, authenticated_user, product_evidence_logger):
        test_name = "Create product with missing required fields"

        try:
            headers = authenticated_user["headers"]
            invalid_data = {
                # Missing 'name' and 'price'
                "quantity": 10
            }

            post_response = requests.post(f"{BASE_URL}/products", headers=headers, json=invalid_data, timeout=10)
            success = post_response.status_code == 400
            details = f"Expected 400 for missing fields, got {post_response.status_code}"
            product_evidence_logger.log_test_result(test_name, success, details, post_response.json() if post_response.text else {})
            assert success, f"Should reject missing required fields: {details}"
        
        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception: {str(e)}")
            pytest.fail(f"Test failed: {str(e)}")


class TestProductServiceEdgeCases:
    def test_update_nonexistent_product(self, authenticated_user, product_evidence_logger):
        test_name = "Update nonexistent product"

        try:
            headers = authenticated_user["headers"]
            update_data = {
                "id": 999999,  # Non-existent ID
                "name": "Updated Name"
            }

            put_response = requests.put(f"{BASE_URL}/products", headers=headers, json=update_data, timeout=10)
            success = put_response.status_code == 404
            details = f"Expected 404 for non-existent product id, got {put_response.status_code}"
            product_evidence_logger.log_test_result(test_name, success, details, put_response.json() if put_response.text else {})
            assert success, f"Should return 404 for non-existent product: {details}"

        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception: {str(e)}")
            pytest.fail(f"Test failed: {str(e)}")
    

    def test_delete_nonexistent_product(self, authenticated_user, product_evidence_logger):
        test_name = "Delete nonexistent product"

        try:
            headers = authenticated_user["headers"]
            update_data = {
                "id": 999999,  # Non-existent ID
            }

            delete_response = requests.delete(f"{BASE_URL}/products", headers=headers, json=update_data, timeout=10)
            success = delete_response.status_code == 404
            details = f"Expected 404 for non-existent product id, got {delete_response.status_code}"
            product_evidence_logger.log_test_result(test_name, success, details, delete_response.json() if delete_response.text else {})
            assert success, f"Should return 404 for non-existent product: {details}"

        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception: {str(e)}")
            pytest.fail(f"Test failed: {str(e)}")
    

    def test_get_empty_product_list(self, product_test_auth_helpers, product_evidence_logger):
        test_name = "Get product list for user with no products"

        try:
            new_user = product_test_auth_helpers.create_test_user()
            headers = new_user["headers"]
            
            get_response = requests.get(f"{BASE_URL}/products", headers=headers, timeout=10)
            success = get_response.status_code == 200
            
            if success:
                data = get_response.json()
                has_empty_list = data.get("products") == []
                has_empty_message = data.get("message") == "No products found"
                success = success and has_empty_list and has_empty_message
            
            details = (f"Status: {get_response.status_code}, " f"Products count: {len(data.get('products', [])) if success else 'N/A'}")
            product_evidence_logger.log_test_result(test_name, success, details, data if success else {})
            assert success, f"Should handle empty product list: {details}"

        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception: {str(e)}")
            pytest.fail(f"Test failed: {str(e)}")

    
    def test_create_product_with_max_values(self, authenticated_user, product_evidence_logger):
        test_name = "Create Product with Maximum Values"
        
        try:
            headers = authenticated_user["headers"]
            
            # Test with maximum values (based on validators)
            max_data = {
                "name": "A" * 254,  # Max 254 characters
                "price": 9999.99,   # Max price
                "quantity": 9999,   # Max quantity
                "description": "Test description"
            }
            
            response = requests.post(f"{BASE_URL}/products", headers=headers, json=max_data, timeout=10)
            success = response.status_code in [200, 201]
            
            details = f"Status: {response.status_code} for max values"
            product_evidence_logger.log_test_result(test_name, success, details, response.json() if response.text else {})
            assert success, f"Should accept maximum valid values: {details}"
            
        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception: {str(e)}")
            pytest.fail(f"Test failed: {str(e)}")


class TestProductServiceMultiUser:
     def test_user_cannot_access_other_user_products(self, product_test_auth_helpers, product_evidence_logger):
        test_name = "User Cannot Access Other User's Products"
        
        try:
            user1 = product_test_auth_helpers.create_test_user()
            user2 = product_test_auth_helpers.create_test_user()

            product_data = {
                "name": "User1 Product",
                "price": 29.99,
                "quantity": 10
            }
            
            create_response = requests.post(f"{BASE_URL}/products", headers=user1["headers"], json=product_data, timeout=10)
            
            if create_response.status_code == 201:
                product_id = create_response.json().get("id")
                
                # User2 tries to access products
                get_response = requests.get(f"{BASE_URL}/products", headers=user2["headers"], timeout=10)
                
                if get_response.status_code == 200:
                    user2_products = get_response.json().get("products", [])
                    # Verify that User2 doesn't see User1's product
                    product_not_found = all(p.get("id") != product_id for p in user2_products)
                    success = product_not_found
                    
                    details = (f"User2 products count: {len(user2_products)}, "
                              f"User1 product found by User2: {not product_not_found}")
                    
                    product_evidence_logger.log_test_result(test_name, success, details, {
                        "user1_product_id": product_id,
                        "user2_products_count": len(user2_products)
                    })
                    assert success, f"User2 should not see User1's product: {details}"
                    
        except Exception as e:
            product_evidence_logger.log_test_result(test_name, False, f"Exception: {str(e)}")
            pytest.fail(f"Test failed: {str(e)}")


if __name__ == "__main__":
    # Run tests directly if needed
    pytest.main([__file__, "-v", "--tb=short"])