import pytest, requests, time, os, uuid, json
from datetime import datetime
from typing import Dict, List

def get_service_port():
    print("Environment Variables:")
    print(f"FLASK_RUN_PORT: {os.getenv('FLASK_RUN_PORT')}")
    print(f"STAGING_PRODUCT_PORT: {os.getenv('STAGING_PRODUCT_PORT')}")
    print(f"PRODUCT_SERVICE_PORT: {os.getenv('PRODUCT_SERVICE_PORT')}")
    print(f"Inside Docker container? {os.path.exists('/.dockerenv')}")

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


def get_user_service_port():
    if os.path.exists('/.dockerenv'):
        # Inside container, user-service runs on its internal port
        # But we need to know how to reach it from product-service container
        user_port = os.getenv("USER_PORT")
        if user_port:
            return user_port
        
        # Check if we have USER_SERVICE_URL to extract port
        user_url = os.getenv("USER_SERVICE_URL")
        if user_url and ":" in user_url:
            # Extract port from URL like http://user-service:4001
            port_part = user_url.split(":")[-1].replace("/", "")
            if port_part.isdigit():
                return port_part
    
    # Outside container or fallback
    staging_port = os.getenv("STAGING_USER_PORT")
    if staging_port:
        return staging_port
    
    dev_port = os.getenv("USER_SERVICE_PORT")
    if dev_port:
        return dev_port
    
    return "3001"


def get_base_urls():
    product_port = get_service_port()
    user_port = get_user_service_port()

    product_port = get_service_port()
    user_port = get_user_service_port()
    
    # Determine hostnames
    if os.path.exists('/.dockerenv'):
        # Inside Docker container
        product_host = "product-service"
        user_host = "user-service"
    else:
        # Outside container
        product_host = "localhost"
        user_host = "localhost"
    
    product_url = f"http://{product_host}:{product_port}"
    user_url = f"http://{user_host}:{user_port}"
    
    return product_url, user_url

# Get URLs
PRODUCT_SERVICE_URL, USER_SERVICE_URL = get_base_urls()

print("FUNCTIONAL TESTS - AUTO DETECTED ENVIRONMENT")
print(f"Running in Docker: {os.path.exists('/.dockerenv')}")
print(f"Product Service URL: {PRODUCT_SERVICE_URL}")
print(f"User Service URL: {USER_SERVICE_URL}")

# Connection test before running tests
print("Checking if Product Service is up")
try:
    test_response = requests.get(f"{PRODUCT_SERVICE_URL}/health", timeout=10)
    print(f"Connection estabilished, status code: {test_response.status_code}")
    print(f"response: {test_response.text[:100]}") # First 100 characters of the response
except Exception as e:
    print(f"Failed to connect to Product Service at {PRODUCT_SERVICE_URL}: {str(e)}")
    print("Tests will likely fail")

print("Checking if User Service is up")
try:
    test_response = requests.get(f"{USER_SERVICE_URL}/health", timeout=10)
    print(f"Connection estabilished, status code: {test_response.status_code}")
    print(f"response: {test_response.text[:100]}")
except Exception as e:
    print(f"Failed to connect to User Service at {USER_SERVICE_URL}: {str(e)}")
    print("Tests will likely fail")

class ProductFunctionalHelpers:

    @staticmethod
    def generate_unique_email() -> str: #-> str = type hinting, show that the function returns a string
        unique_id = uuid.uuid4().hex[:8]
        return f"func_product_{unique_id}@example.com"
    
    @staticmethod
    def generate_product_data(product_number:int = 1) -> Dict:
        timestamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        base_price = 10.00 + product_number
        base_quantity = 5 + product_number

        return {
            "name": f"functional product {product_number} at {timestamp}",
            "price": round(base_price * 1.5, 2),
            "quantity": base_quantity,
            "description": f"Detailed description of functional product #{product_number} created at {timestamp}"
        }
    
    @staticmethod
    def create_test_user() -> Dict:
        email = ProductFunctionalHelpers.generate_unique_email()

        register_response = requests.post(f"{USER_SERVICE_URL}/register", json={"email": email, "password": "FuncTest@123"},timeout=10)

        if register_response.status_code not in [200,201]:
            raise Exception(f"User registration failed during product functional test setup: {register_response.text}")
        time.sleep(1)

        login_response = requests.post(f"{USER_SERVICE_URL}/login",json={"email": email, "password": "FuncTest@123"},timeout=10)

        if login_response.status_code != 200:
            # Retry once
            time.sleep(1)
            login_response = requests.post(
                f"{USER_SERVICE_URL}/login",
                json={"email": email, "password": "FuncTest@123"},
                timeout=10
            )
        
        if login_response.status_code != 200:
            raise Exception(f"User login failed: {login_response.text}")
        
        login_data = login_response.json()
        return {
            "email": email,
            "user_id": login_data.get("user_id"),
            "token": login_data.get("token"),
            "headers": {"Authorization": f"Bearer {login_data.get('token')}"}
        }
    
    @staticmethod
    def wait_for_service(url: str, max_retries: int = 10, delay: int = 2) -> bool:
        """Wait for service to be available"""
        for attempt in range(max_retries):
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code == 200:
                    print(f"Service at {url} is healthy")
                    return True
            except requests.exceptions.ConnectionError:
                pass
            
            print(f"Waiting for service at {url}(attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)
        
        return False

class TestProductServiceFunctional:

    def setup_method(self):
        print("\n" + "="*60)
        print(f"Starting functional test")
        print("="*60)

        if not ProductFunctionalHelpers.wait_for_service(PRODUCT_SERVICE_URL):
            pytest.skip("Product Service not available")
        if not ProductFunctionalHelpers.wait_for_service(USER_SERVICE_URL):
            pytest.skip("User Service not available")

    def teardown_method(self):
        """Cleanup after each test"""
        print(f"\nCompleted test")
        print("-"*60)
    

    def test_complete_product_lifecycle(self):
        test_start_time = datetime.now()
        print(f"Test started at: {test_start_time}")
        
        # 1. Create test user
        print("\n1. Creating test user")
        user_data = ProductFunctionalHelpers.create_test_user()
        print(f"   User created: {user_data['email']}")
        
        # 2. Create product
        print("\n2. Creating product")
        product_data = ProductFunctionalHelpers.generate_product_data(1)
        
        create_response = requests.post(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user_data["headers"],
            json=product_data,
            timeout=10
        )
        
        print(f"Create response: {create_response.status_code}")
        assert create_response.status_code == 201, f"Product creation failed: {create_response.text}"
        
        create_result = create_response.json()
        product_id = create_result.get("id")
        assert product_id is not None, "Product ID missing in response"
        print(f"Product created with ID: {product_id}")
        
        # 3. Get products (should contain the created product)
        print("\n3. Getting product list")
        get_response = requests.get(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user_data["headers"],
            timeout=10
        )
        
        assert get_response.status_code == 200, f"Get products failed: {get_response.text}"
        
        get_result = get_response.json()
        products = get_result.get("products", [])
        assert len(products) > 0, "No products found for user"
        
        # Find our product in the list
        created_product = next((p for p in products if p["id"] == product_id), None)
        assert created_product is not None, "Created product not found in list"
        print(f"Product found in list: {created_product['name']}")
        
        # 4. Update product
        print("\n4. Updating product")
        update_data = {
            "id": product_id,
            "name": f"updated - {product_data['name']}",
            "price": round(product_data["price"] * 1.1, 2),  # 10% increase
            "description": f"updated description - {datetime.now()}"
        }
        
        update_response = requests.put(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user_data["headers"],
            json=update_data,
            timeout=10
        )
        
        assert update_response.status_code == 200, f"Product update failed: {update_response.text}"
        print(f"Product updated successfully")
        
        # 5. Verify update
        print("\n5. Verifying update")
        get_response_after_update = requests.get(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user_data["headers"],
            timeout=10
        )
        
        products_after_update = get_response_after_update.json().get("products", [])
        updated_product = next((p for p in products_after_update if p["id"] == product_id), None)
        
        assert updated_product["name"] == update_data["name"].lower(), "Name not updated"
        assert updated_product["price"] == update_data["price"], "Price not updated"
        print(f"   Update verified: {updated_product['name']} - ${updated_product['price']}")
        
        # 6. Delete product
        print("\n6. Deleting product")
        delete_response = requests.delete(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user_data["headers"],
            json={"id": product_id},
            timeout=10
        )
        
        assert delete_response.status_code == 200, f"Product deletion failed: {delete_response.text}"
        print(f"Product deleted successfully")
        
        # 7. Verify deletion
        print("\n7. Verifying deletion")
        get_response_after_delete = requests.get(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user_data["headers"],
            timeout=10
        )
        
        products_after_delete = get_response_after_delete.json().get("products", [])
        deleted_product_still_exists = any(p["id"] == product_id for p in products_after_delete)
        assert not deleted_product_still_exists, "Product still exists after deletion"
        print(f"Deletion verified - product no longer in list")
        
        test_end_time = datetime.now()
        duration = (test_end_time - test_start_time).total_seconds()
        
        print(f"\n Complete product lifecycle test PASSED")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Steps: User Creation → Product Creation → Read → Update → Delete → Verification")
    
    def test_multiple_products_management(self):
        print("Testing multiple products management")
        
        # Create user
        user_data = ProductFunctionalHelpers.create_test_user()
        
        product_ids = []
        
        # Create 3 products
        for i in range(1, 4):
            product_data = ProductFunctionalHelpers.generate_product_data(i)
            
            response = requests.post(
                f"{PRODUCT_SERVICE_URL}/products",
                headers=user_data["headers"],
                json=product_data,
                timeout=10
            )
            
            assert response.status_code == 201, f"Failed to create product #{i}: {response.text}"
            product_id = response.json().get("id")
            product_ids.append(product_id)
            print(f"   Created product #{i}: ID={product_id}, Name='{product_data['name']}'")
        
        # Get all products
        get_response = requests.get(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user_data["headers"],
            timeout=10
        )
        
        products = get_response.json().get("products", [])
        assert len(products) == 3, f"Expected 3 products, found {len(products)}"
        print(f"   Retrieved {len(products)} products")
        
        # Update one product
        update_data = {
            "id": product_ids[1],  # Update the second product
            "name": "SPECIALLY UPDATED PRODUCT",
            "quantity": 999
        }
        
        update_response = requests.put(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user_data["headers"],
            json=update_data,
            timeout=10
        )
        
        assert update_response.status_code == 200, f"Failed to update product: {update_response.text}"
        print(f"Updated product ID {product_ids[1]}")
        
        # Delete all products
        for i, product_id in enumerate(product_ids, 1):
            delete_response = requests.delete(
                f"{PRODUCT_SERVICE_URL}/products",
                headers=user_data["headers"],
                json={"id": product_id},
                timeout=10
            )
            
            assert delete_response.status_code == 200, f"Failed to delete product #{i}: {delete_response.text}"
            print(f"   Deleted product #{i}: ID={product_id}")
        
        # Verify all deleted
        final_get_response = requests.get(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user_data["headers"],
            timeout=10
        )
        
        final_products = final_get_response.json().get("products", [])
        assert len(final_products) == 0, f"Expected 0 products after deletion, found {len(final_products)}"
        
        print(f"\n Multiple products management test PASSED")
        print(f"Created: 3 products")
        print(f"Updated: 1 product")
        print(f"Deleted: 3 products")
    
    
    def test_product_validation_scenarios(self):
        print("Testing product validation scenarios")
        
        user_data = ProductFunctionalHelpers.create_test_user()
        test_cases = [
            {
                "name": "Empty product name",
                "data": {"name": "", "price": 10.99},
                "expected_error": "missing required field"
            },
            {
                "name": "Negative price",
                "data": {"name": "Test Product", "price": -5.99},
                "expected_error": "price does not meet requirements"
            },
            {
                "name": "Price too high",
                "data": {"name": "Test Product", "price": 15000.00},
                "expected_error": "price does not meet requirements"
            },
            {
                "name": "Negative quantity",
                "data": {"name": "Test Product", "price": 10.99, "quantity": -5},
                "expected_error": "Invalid quantity"
            },
            {
                "name": "Quantity too high",
                "data": {"name": "Test Product", "price": 10.99, "quantity": 15000},
                "expected_error": "Invalid quantity"
            },
            {
                "name": "Missing price",
                "data": {"name": "Test Product"},
                "expected_error": "missing required field"
            },
            {
                "name": "Missing name",
                "data": {"price": 10.99},
                "expected_error": "missing required field"
            },
            {
                "name": "Invalid price type",
                "data": {"name": "Test Product", "price": "not-a-number"},
                "expected_error": "price does not meet requirements"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            response = requests.post(
                f"{PRODUCT_SERVICE_URL}/products",
                headers=user_data["headers"],
                json=test_case["data"],
                timeout=10
            )
            
            assert response.status_code == 400, f"Test case '{test_case['name']}' should fail but got {response.status_code}"
            
            error_data = response.json()
            error_msg = str(error_data).lower()
            
            # Check if expected error keyword is in response
            assert test_case["expected_error"].lower() in error_msg, \
                f"Expected error '{test_case['expected_error']}' not found in: {error_msg}"
            
            print(f" Validation test #{i}: '{test_case['name']}' correctly rejected")
        
        print(f"\n All validation scenarios test PASSED")
        print(f"   Tested: {len(test_cases)} validation scenarios")
    
    
    def test_edge_cases(self):
        """Test edge cases and boundary values"""
        print("Testing edge cases and boundary values")
        
        user_data = ProductFunctionalHelpers.create_test_user()
        
        # Test 1: Zero price (should be allowed)
        print("\n1. Testing zero price...")
        zero_price_data = {
            "name": "Free Product",
            "price": 0.00,
            "quantity": 1
        }
        
        response = requests.post(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user_data["headers"],
            json=zero_price_data,
            timeout=10
        )
        
        assert response.status_code == 201, f"Zero price should be allowed: {response.text}"
        zero_price_product_id = response.json().get("id")
        print(f"Zero price product created: ID={zero_price_product_id}")
        
        # Test 2: Zero quantity (should be allowed)
        print("\n2. Testing zero quantity...")
        zero_quantity_data = {
            "name": "Out of Stock Product",
            "price": 19.99,
            "quantity": 0
        }
        
        response = requests.post(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user_data["headers"],
            json=zero_quantity_data,
            timeout=10
        )
        
        assert response.status_code == 201, f"Zero quantity should be allowed: {response.text}"
        print(f"Zero quantity product created")
        
        # Test 3: Maximum values
        print("\n3. Testing maximum allowed values...")
        max_values_data = {
            "name": "A" * 254,  # Max length
            "price": 9999.99,   # Max price
            "quantity": 9999,   # Max quantity
            "description": "D" * 2000  # Max description
        }
        
        response = requests.post(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user_data["headers"],
            json=max_values_data,
            timeout=10
        )
        
        assert response.status_code == 201, f"Maximum values should be allowed: {response.text}"
        max_product_id = response.json().get("id")
        print(f"Maximum values product created: ID={max_product_id}")
        
        # Cleanup
        for product_id in [zero_price_product_id, max_product_id]:
            requests.delete(
                f"{PRODUCT_SERVICE_URL}/products",
                headers=user_data["headers"],
                json={"id": product_id},
                timeout=10
            )
        
        print(f"\n Edge cases test PASSED")
        print(f"Tested: Zero price, Zero quantity, Maximum values")
    
    
    def test_user_isolation_security(self):
        print("Testing user isolation and security")
        
        # Create two different users
        print("\n1. Creating two test users")
        user1 = ProductFunctionalHelpers.create_test_user()
        user2 = ProductFunctionalHelpers.create_test_user()
        
        print(f"User 1: {user1['email']}")
        print(f"User 2: {user2['email']}")
        
        # User 1 creates a product
        print("\n2. User 1 creates a product")
        product_data = ProductFunctionalHelpers.generate_product_data(1)
        
        create_response = requests.post(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user1["headers"],
            json=product_data,
            timeout=10
        )
        
        assert create_response.status_code == 201, f"User1 failed to create product: {create_response.text}"
        product_id = create_response.json().get("id")
        print(f"User 1 created product: ID={product_id}")
        
        # User 2 tries to GET User 1's product (should not see it)
        print("\n3. User 2 tries to list products")
        user2_get_response = requests.get(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user2["headers"],
            timeout=10
        )
        
        user2_products = user2_get_response.json().get("products", [])
        user1_product_found_by_user2 = any(p["id"] == product_id for p in user2_products)
        assert not user1_product_found_by_user2, "User 2 should not see User 1's product"
        print(f"User 2 cannot see User 1's product")
        
        # User 2 tries to UPDATE User 1's product (should fail)
        print("\n4. User 2 tries to update User 1's product")
        update_attempt = {
            "id": product_id,
            "name": "HACKED BY USER2",
            "price": 0.01
        }
        
        update_response = requests.put(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user2["headers"],
            json=update_attempt,
            timeout=10
        )
        
        # Should get 404 (not found) or similar error
        assert update_response.status_code in [404, 403], \
            f"User 2 should not be able to update User 1's product. Got: {update_response.status_code}"
        print(f"User 2 cannot update User 1's product")
        
        # User 2 tries to DELETE User 1's product (should fail)
        print("\n5. User 2 tries to delete User 1's product")
        delete_response = requests.delete(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user2["headers"],
            json={"id": product_id},
            timeout=10
        )
        
        assert delete_response.status_code in [404, 403], \
            f"User 2 should not be able to delete User 1's product. Got: {delete_response.status_code}"
        print(f"User 2 cannot delete User 1's product")
        
        # Verify User 1's product still exists and unchanged
        print("\n6. Verifying User 1's product is intact")
        user1_get_response = requests.get(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user1["headers"],
            timeout=10
        )
        
        user1_products = user1_get_response.json().get("products", [])
        user1_product = next((p for p in user1_products if p["id"] == product_id), None)
        assert user1_product is not None, "User 1's product disappeared"
        assert user1_product["name"] == product_data["name"].lower(), "User 1's product was modified"
        print(f"User 1's product is still intact: {user1_product['name']}")
        
        # Cleanup
        requests.delete(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user1["headers"],
            json={"id": product_id},
            timeout=10
        )
        
        print(f"\n User isolation and security test PASSED")
        print(f"Tested: Data isolation, Update prevention, Delete prevention")
    
    
    def test_basic_performance(self):
        print("Testing basic performance with sequential operations")
        
        user_data = ProductFunctionalHelpers.create_test_user()
        operations = []
        
        # Time the operations
        start_time = time.time()
        
        # Create 5 products
        product_ids = []
        for i in range(5):
            product_data = ProductFunctionalHelpers.generate_product_data(i + 1)
            
            op_start = time.time()
            response = requests.post(
                f"{PRODUCT_SERVICE_URL}/products",
                headers=user_data["headers"],
                json=product_data,
                timeout=10
            )
            op_end = time.time()
            
            assert response.status_code == 201
            product_id = response.json().get("id")
            product_ids.append(product_id)
            
            operations.append({
                "type": "create",
                "duration": op_end - op_start,
                "success": response.status_code == 201
            })
        
        # Get products
        op_start = time.time()
        get_response = requests.get(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user_data["headers"],
            timeout=10
        )
        op_end = time.time()
        
        assert get_response.status_code == 200
        operations.append({
            "type": "get_all",
            "duration": op_end - op_start,
            "success": get_response.status_code == 200
        })
        
        # Update one product
        if product_ids:
            update_data = {
                "id": product_ids[2],
                "name": "Performance Test Updated"
            }
            
            op_start = time.time()
            update_response = requests.put(
                f"{PRODUCT_SERVICE_URL}/products",
                headers=user_data["headers"],
                json=update_data,
                timeout=10
            )
            op_end = time.time()
            
            assert update_response.status_code == 200
            operations.append({
                "type": "update",
                "duration": op_end - op_start,
                "success": update_response.status_code == 200
            })
        
        # Delete all products
        for product_id in product_ids:
            op_start = time.time()
            delete_response = requests.delete(
                f"{PRODUCT_SERVICE_URL}/products",
                headers=user_data["headers"],
                json={"id": product_id},
                timeout=10
            )
            op_end = time.time()
            
            operations.append({
                "type": "delete",
                "duration": op_end - op_start,
                "success": delete_response.status_code == 200
            })
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        create_times = [op["duration"] for op in operations if op["type"] == "create"]
        avg_create_time = sum(create_times) / len(create_times) if create_times else 0
        
        successful_ops = sum(1 for op in operations if op["success"])
        success_rate = (successful_ops / len(operations)) * 100
        
        print(f"\nPerformance Results:")
        print(f"Total operations: {len(operations)}")
        print(f"Successful operations: {successful_ops} ({success_rate:.1f}%)")
        print(f"Total test duration: {total_time:.2f} seconds")
        print(f"Average create time: {avg_create_time:.3f} seconds")
        print(f"Operations per second: {len(operations) / total_time:.2f}")
        
        # Assert reasonable performance
        assert success_rate == 100, f"Not all operations succeeded: {success_rate:.1f}%"
        assert total_time < 30, f"Test took too long: {total_time:.2f} seconds"
        
        print(f"\n Basic performance test PASSED")
    
    def test_service_resilience(self):
        print("Testing service resilience")
        
        user_data = ProductFunctionalHelpers.create_test_user()
        
        # Test 1: Invalid token
        print("\n1. Testing with invalid token")
        invalid_headers = {"Authorization": "Bearer invalid_token_here"}
        
        response = requests.get(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=invalid_headers,
            timeout=10
        )
        
        assert response.status_code == 401, f"Invalid token should be rejected: {response.status_code}"
        print(f"Invalid token correctly rejected")
        
        # Test 2: Malformed JSON
        print("\n2. Testing with malformed JSON")
        malformed_headers = user_data["headers"].copy()
        malformed_headers["Content-Type"] = "application/json"
        
        response = requests.post(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=malformed_headers,
            data="{malformed json here",
            timeout=10
        )
        
        assert response.status_code == 400, f"Malformed JSON should be rejected: {response.status_code}"
        print(f" Malformed JSON correctly rejected")
        
        # Test 3: Very large request
        print("\n3. Testing with very large request")
        large_data = {
            "name": "A" * 1000,  # Exceeds max length
            "price": 10.99,
            "description": "D" * 3000  # Exceeds max length
        }
        
        response = requests.post(
            f"{PRODUCT_SERVICE_URL}/products",
            headers=user_data["headers"],
            json=large_data,
            timeout=10
        )
        
        # Should get validation error
        assert response.status_code == 400, f"Oversized request should be rejected: {response.status_code}"
        print(f"Oversized request correctly rejected")
        
        print(f"\n Service resilience test PASSED")
        print(f" Tested: Invalid tokens, Malformed JSON, Oversized requests")


def run_all_functional_tests():
    print("PRODUCT SERVICE - FUNCTIONAL TESTS SUITE")

    
    test_start_time = datetime.now()
    print(f"Test execution started: {test_start_time}")
    print(f"Product Service URL: {PRODUCT_SERVICE_URL}")
    print(f"User Service URL: {USER_SERVICE_URL}")

    
    # Create test instance
    test_suite = TestProductServiceFunctional()
    
    # List of test methods to run
    test_methods = [
        test_suite.test_complete_product_lifecycle,
        test_suite.test_multiple_products_management,
        test_suite.test_product_validation_scenarios,
        test_suite.test_edge_cases,
        test_suite.test_user_isolation_security,
        test_suite.test_basic_performance,
        test_suite.test_service_resilience,
    ]
    
    results = []
    
    for test_method in test_methods:
        test_name = test_method.__name__
        
        try:
            # Setup
            test_suite.setup_method()
            
            # Run test
            test_method()
            
            # Record success
            results.append({
                "test": test_name,
                "status": "PASS",
                "error": None
            })
            
            print(f"{test_name}: PASSED")
            
        except AssertionError as e:
            results.append({
                "test": test_name,
                "status": "FAIL",
                "error": str(e)
            })
            
            print(f"{test_name}: FAILED - {str(e)}")
            
        except Exception as e:
            results.append({
                "test": test_name,
                "status": "ERROR",
                "error": f"Unexpected error: {str(e)}"
            })
            
            print(f" {test_name}: ERROR - {str(e)}")
        
        finally:
            # Teardown
            test_suite.teardown_method()
    
    # Generate summary report
    test_end_time = datetime.now()
    total_duration = (test_end_time - test_start_time).total_seconds()
    
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY REPORT")
    print("=" * 70)
    print(f"Total tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Errors: {errors}")
    print(f"Success rate: {(passed / len(results)) * 100:.1f}%")
    print(f"Total duration: {total_duration:.2f} seconds")
    print(f"Started: {test_start_time}")
    print(f"Ended: {test_end_time}")
    print("-" * 70)
    
    if failed > 0 or errors > 0:
        print("\nFAILED/ERROR TESTS:")
        for result in results:
            if result["status"] in ["FAIL", "ERROR"]:
                print(f"  • {result['test']}: {result['error']}")
    
    print("\n" + "=" * 70)
    
    # Return overall success
    return failed == 0 and errors == 0


if __name__ == "__main__":
    # Run all tests
    success = run_all_functional_tests()
    
    # Exit with appropriate code
    exit(0 if success else 1)