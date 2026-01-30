from unittest import mock
import pytest, sys, os
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from product_app import app, token_required, get_db_connection
from pymysql import Error


class TestProductTokenRequiredDecorator:
    
    def test_token_required_missing_token(self):
        @token_required
        def protected_function(user_id):
            return "Success"
        
        with app.test_request_context():
            from flask import request

            with patch.object(request,'headers',{'Authorization': None}):
                result = protected_function()
                assert result[1] == 401 
                assert "Token is missing" in str(result[0].data)
    
    @patch('product_app.jwt.decode')
    def test_token_required_valid_token(self, mock_jwt_decode):

        mock_jwt_decode.return_value = {'user_id': 333, 'email': 'test_product_unit@example.com'}

        mock_func = Mock(return_value="Success")

        decorated_func = token_required(mock_func)

        with app.test_request_context(headers={'Authorization': 'Bearer valid.jwt.token'}):

            result = decorated_func()

            mock_func.assert_called_once_with(333)
            assert result == "Success"
    
    
    @patch('product_app.jwt.decode')
    def test_token_required_expired_token(self, mock_jwt_decode):

        from jwt import ExpiredSignatureError
        mock_jwt_decode.side_effect = ExpiredSignatureError("Token expired")

        @token_required
        def protected_function(user_id):
            return "Success"
        
        with app.test_request_context(headers={'Authorization': 'Bearer expired.token'}):
            result = protected_function()

            assert result[1] == 401
            assert "Token has expired" in str(result[0].data)
    

    @patch('product_app.jwt.decode')
    def test_token_required_invalid_token(self, mock_jwt_decode):

        from jwt import InvalidTokenError
        mock_jwt_decode.side_effect = InvalidTokenError("Invalid token")

        @token_required
        def protected_function(user_id):
            return "Success"
        
        with app.test_request_context(headers={'Authorization': 'Bearer invalid.token'}):
            result = protected_function()

            assert result[1] == 401
            assert "Invalid token" in str(result[0].data)
    

class TestGetDbConnection:
    
    @patch('product_app.pymysql.connect')
    def test_get_db_connection_success(self, mock_connect):
        
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        with app.app_context():
            app.config.update({
                "MYSQL_HOST": "localhost",
                "MYSQL_USER": "test_product_user",
                "MYSQL_PASSWORD": "test_product_pass",
                "MYSQL_DB": "test_product_db",
                "MYSQL_PORT": "3306"
            })
            
            import pymysql
            conn = get_db_connection()

            assert conn == mock_conn
            mock_connect.assert_called_once_with(
                host="localhost",
                user="test_product_user",
                password="test_product_pass",
                db="test_product_db",
                port=3306,
                cursorclass=pymysql.cursors.DictCursor
            )
    
    @patch('product_app.pymysql.connect')
    def test_get_db_connection_failure(self, mock_connect):

        mock_connect.side_effect = Error("Connection failed")

        with app.app_context():
            app.config.update({
                "MYSQL_HOST": "localhost",
                "MYSQL_USER": "test_product_user",
                "MYSQL_PASSWORD": "test_product_pass",
                "MYSQL_DB": "test_product_db",
                "MYSQL_PORT": "3306"
            })

            conn = get_db_connection()
            assert conn is None


class TestProductValidatorsIntegration:

    def test_product_import_validators(self):

        from product_app import ProductValidator
        assert ProductValidator is not None

        assert hasattr(ProductValidator,'validate_product')
        assert hasattr(ProductValidator,'validate_product_quantity')
        assert hasattr(ProductValidator,'validate_product_price')
        assert hasattr(ProductValidator,'validate_product_description')
        assert hasattr(ProductValidator,'validate_registration_object')


class TestProductAppRoutesWithMocks:

    @patch('product_app.ProductValidator.validate_registration_object')
    @patch('product_app.get_db_connection')
    @patch('product_app.jwt.decode')
    def test_product_registration_route_success(self,mock_jwt_decode,mock_db, mock_validate):
        
        #mock jwt decode to simulate valid user login to create product
        mock_jwt_decode.return_value = {'user_id': 333, 'email': 'test_product_unit@example.com'}

        #Configure mock object for product data validation
        mock_validate.return_value = (True, {
        "product_name": "test product",
        "price": 29.99,
        "quantity": 10,
        "description": "test description"
    })
        
        #Congiure mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_conn
        mock_cursor.lastrowid = 1

        with app.test_client() as client:
            with app.app_context():
                with patch('product_app.ProductValidator.validate_registration_object', mock_validate):
                    with patch('product_app.get_db_connection', mock_db):
                        with patch('product_app.jwt.decode', mock_jwt_decode):
                            response = client.post(
                                '/products',
                                json={
                                    "product_name": "test product",
                                    "price": 29.99,
                                    "quantity": 10,
                                    "description": "test description"
                                },
                                headers={'Authorization': 'Bearer valid.jwt.token'},
                                content_type='application/json'
                            )
        assert response.status_code == 201
        mock_jwt_decode.assert_called_once_with(
            'valid.jwt.token',
            mock.ANY, #Object any to ignore the secret key value in the token required decorator
            algorithms=["HS256"]
        )

    @patch('product_app.ProductValidator.validate_registration_object')
    @patch('product_app.get_db_connection')
    @patch('product_app.jwt.decode')
    def test_product_registration_route_failure(self,mock_jwt_decode,mock_db, mock_validate):
        mock_jwt_decode.return_value = {'user_id': 333, 'email': 'test_product_unit@example.com'}

        #Configure mock object for product data validation
        error_msg = { "error":"missing required field:"}
        mock_validate.return_value = (False, error_msg)
        with app.test_client() as client:
            with app.app_context():
                with patch('product_app.ProductValidator.validate_registration_object', mock_validate):
                    with patch('product_app.get_db_connection', mock_db):
                        with patch('product_app.jwt.decode', mock_jwt_decode):
                            response = client.post(
                                '/products',
                                json={
                                    "product_name": "",#Missing name should invalidate product creation
                                    "price": 29.99,
                                    "quantity": 10,
                                    "description": "test description"
                                },
                                headers={'Authorization': 'Bearer valid.jwt.token'},
                                content_type='application/json'
                            )
                            assert response.status_code == 400
                            assert response.get_json() == error_msg
    
    
    @patch('product_app.get_db_connection')
    @patch('product_app.jwt.decode')
    def test_product_get_route_success(self,mock_jwt_decode,mock_db):
        mock_jwt_decode.return_value = {'user_id': 333, 'email': 'test_product_unit@example.com'}

        db_data = [{
        "id": 1,
        "product_name": "test product",
        "price": 29.99,
        "quantity": 10,
        "description": "test description",
        "created_by": 333
    }]
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_conn
        mock_cursor.fetchall.return_value = db_data
        with app.test_client() as client:
            with app.app_context():
                    with patch('product_app.get_db_connection', mock_db):
                        with patch('product_app.jwt.decode', mock_jwt_decode):
                            response = client.get(
                                '/products',
                                headers={'Authorization': 'Bearer valid.jwt.token'}
                            )
                            assert response.status_code == 200
                            assert response.get_json() == {"products": db_data}

    @patch('product_app.get_db_connection')
    @patch('product_app.jwt.decode')
    def test_product_get_empty(self, mock_jwt_decode, mock_db):
        mock_jwt_decode.return_value = {'user_id': 333, 'email': 'test_product_unit@example.com'}
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_conn
        mock_cursor.fetchall.return_value = []  # empty list to simulate no products
    
        with app.test_client() as client: # Removal of unnecessary app.app_context() for study reasons, as test_client provides context automatically
            response = client.get(
                '/products',
                headers={'Authorization': 'Bearer valid.jwt.token'}
            )
    
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data["message"] == "No products found"
        assert response_data["products"] == []

    @patch('product_app.ProductValidator.validate_product_quantity')
    @patch('product_app.ProductValidator.validate_product_price')
    @patch('product_app.ProductValidator.validate_product')
    @patch('product_app.get_db_connection')
    @patch('product_app.jwt.decode')
    def test_product_put_route_success(self, mock_jwt, mock_db, mock_val_name, mock_val_price, mock_val_qty):
        mock_jwt.return_value = {'user_id': 333, 'email': 'test_product_unit@example.com'}

        mock_val_name.return_value = (True, "keybord")
        mock_val_price.return_value = (True, 100.0)
        mock_val_qty.return_value = (True, 5)
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_conn
        mock_cursor.fetchone.return_value = {"id":1}

        with app.test_client() as client:
            update_data = {
                "id":1,
                "name": "keyboard new",
                "price": 39.99,
                "quantity": 2,
            }
            response = client.put('/products',json=update_data, headers={'Authorization': 'Bearer valid.jwt.token'})
            
            assert response.status_code == 200
            assert response.get_json()["message"] == "Product updated successfully"
            assert mock_cursor.execute.call_count == 4 #1 for select + 3 for update fields
            mock_conn.commit.assert_called_once()

    @patch('product_app.get_db_connection')
    @patch('product_app.jwt.decode')
    def test_product_put_route_without_product(self, mock_jwt_decode, mock_db):
        mock_jwt_decode.return_value = {'user_id': 333}
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_conn
        mock_cursor.fetchone.return_value = None 
    
        with app.test_client() as client:
            response = client.put(
                '/products',
                json={"id": 999, "name": "Updated"},
                headers={'Authorization': 'Bearer valid.jwt.token'}
            )
    
        assert response.status_code == 404
        assert "product not found" in response.get_json()["error"].lower()


    @patch('product_app.get_db_connection')
    @patch('product_app.jwt.decode')
    def test_product_delete_route_success(self, mock_jwt, mock_db):
        mock_jwt.return_value = {'user_id': 333, 'email': 'test_product_unit@example.com'}

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_conn
        mock_cursor.fetchone.return_value = {"id":1, "name":"Delete_product"}
        mock_cursor.rowcount = 1 #Simulate one row affected
        
        with app.test_client() as client:
            response = client.delete('/products',
                json={"id":1},
                headers={'Authorization': 'Bearer valid.jwt.token'})
            
            assert response.status_code == 200
            assert response.get_json()["message"] == "Product deleted successfully"
            assert response.get_json()["deleted_product_id"] == 1
            assert mock_cursor.execute.call_count == 2 #1 for select + 1 for delete
            mock_conn.commit.assert_called_once()

    @patch('product_app.get_db_connection')
    @patch('product_app.jwt.decode')
    def test_product_delete_route_without_product(self, mock_jwt, mock_db):
        mock_jwt.return_value = {'user_id': 333, 'email': 'test_product_unit@example.com'}

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_conn
        mock_cursor.fetchone.return_value = None

        with app.test_client() as client:
            response = client.delete('/products',
                json={"id":999},
                headers={'Authorization': 'Bearer valid.jwt.token'}
            )
        
        assert response.status_code == 404
        assert "product not found" in response.get_json()["error"].lower()

class TestProductHealthCheck:

    @patch('product_app.get_db_connection')
    def test_health_check(self, mock_db):
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        
        with app.test_client() as client:
            response = client.get('/health')
            assert response.status_code == 200
            assert response.get_json()["status"] == "healthy"
    
    @patch('product_app.get_db_connection')
    def test_health_check_detailed(self, mock_db):
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        
        with app.test_client() as client:
            response = client.get('/health/detailed')
            assert response.status_code == 200
            data = response.get_json()
            assert "checks" in data
            assert data["checks"]["database_connection"] == True