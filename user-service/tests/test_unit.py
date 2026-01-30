import pytest, sys, os
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, token_required, get_db_connection, token_blacklist, blacklist_expiry
from pymysql import Error
from validators import Validators

class TestTokenRequiredDecorator:

    def test_token_required_missing_token(self):
        @token_required
        def protected_function(user_id):
            return "Success"
        
        #Mocking Flask request without token
        with app.test_request_context(): 
            from flask import request

            with patch.object(request,'headers',{'Authorization': None}): #Using patch to alter existing object attribute: altering the request object and attributing the headers from the request object as None
                result = protected_function()
                assert result[1] == 401 
                assert "Token is missing" in str(result[0].data)

    @patch('app.jwt.decode')#patch that hinder the verification of a real cryptographed ctoken and subbed for a mock
    def test_token_required_valid_token(self, mock_jwt_decode):
        """Test request with valid token"""

        # Mock the JWT decode function
        mock_jwt_decode.return_value = {'user_id': 123, 'email': 'test@example.com'} #Configuring what de decode will return

        #Mock function to test
        mock_func = Mock(return_value="Success") #Mock function that return success

        # Apply decorator
        decorated_func = token_required(mock_func) #decorated function that will only work if has a valid token and apply the function between ()

        # Mocking Flask request with valid token
        with app.test_request_context(headers={'Authorization': 'Bearer valid.jwt.token'}):

            result = decorated_func() # Call the decorated function

            # Verify that the original function was called with correct user_id
            mock_func.assert_called_once_with(123)
            assert result == "Success"
        
    @patch('app.jwt.decode')
    def test_token_required_expired_token(self,mock_jwt_decode):
        """Test with expired token"""

        from jwt import ExpiredSignatureError
        mock_jwt_decode.side_effect = ExpiredSignatureError("Token expired") #side_effect used to throw an ExpiredSignatureError

        @token_required
        def protected_function(user_id):
            return "Success"
            
        with app.test_request_context(headers={'Authorization': 'Bearer expired.token'}):
            result = protected_function()

            assert result[1] == 401
            assert "Token has expired" in str(result[0].data) #.data to access response body from the result


    @patch('app.jwt.decode')
    def test_token_required_invalid_token(self,mock_jwt_decode):
        """Test with invalid token"""

        from jwt import InvalidTokenError
        mock_jwt_decode.side_effect = InvalidTokenError("Token invalid") #side_effect to throw an invalidTokenError

        @token_required
        def protected_function(user_id):
            return "Success"
    
        with app.test_request_context(headers={'Authorization': 'Bearer invalid.token'}):
            result = protected_function()

            assert result[1] == 401
            assert "Invalid token!" in str(result[0].data)

class TestGetDbConnection:

    @patch('app.pymysql.connect')#patch to hinder the real attempt to connect to a real database
    def test_get_db_connection_success(self, mock_connect):
        """"Test databse connection"""

        #Configure mock
        mock_conn = MagicMock() #mock_conn = connection object empty
        mock_connect.return_value = mock_conn #mock_connect = method that attempts the connection, and deliver the connection object, with the configuration data

        # configure app for testing
        with app.app_context(): #app_context simulate the running server to search for the configuration
            app.config.update({
                "MYSQL_HOST": "localhost",
                "MYSQL_USER": "test_user",
                "MYSQL_PASSWORD": "test_pass",
                "MYSQL_DB": "test_db",
                "MYSQL_PORT": "3306"
            })

            # call function
            import pymysql
            conn = get_db_connection()

            assert conn == mock_conn
            mock_connect.assert_called_once_with(
                host="localhost",
                user="test_user",
                password="test_pass",
                database="test_db",
                port=3306,
                cursorclass=pymysql.cursors.DictCursor
            )
    
    @patch('app.pymysql.connect')
    def test_get_db_connection_failure(self, mock_connect):
        """test fail in database connction"""
        # configure mock to raise exception
        mock_connect.side_effect = Error("Connection failed")

        with app.app_context():
            app.config.update({
                "MYSQL_HOST": "localhost",
                "MYSQL_USER": "test",
                "MYSQL_PASSWORD": "test",
                "MYSQL_DB": "test_db",
                "MYSQL_PORT": "3306"
            })

            # call function - return None in case of failure
            conn = get_db_connection()
            assert conn is None

class TestValidatorsIntegration:

    def test_app_imports_validators(self):

        """Test if app imports validators correctly"""
        from app import Validators
        assert Validators is not None

        assert hasattr(Validators, 'validate_email') #hasattr = hasattribute
        assert hasattr(Validators, 'validate_password')
        assert hasattr(Validators, 'validate_registration_data')


class TestAppRoutesWithMocks:
    """Tests for app routes using mocks for database and validators"""
    
    @patch('app.Validators.validate_registration_data') #mock_validate
    @patch('app.get_db_connection') # mock_db
    @patch('app.generate_password_hash') #mock hash
    def test_register_route_success(self, mock_validate, mock_db, mock_hash): # the mock order is important
        """Test route /register with valid data"""
        # Configure mock
        mock_validate.return_value = (True, {
            "email": "test@example.com",
            "password": "RawPass123@"
        })
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor #simulating db_connection cursor
        mock_db.return_value = mock_conn
        mock_hash.return_value = "hashed_password_123@"
        mock_cursor.fetchone.return_value = None  # telling to ignore an equal email - register a new user
        mock_cursor.lastrowid = 456 #ID simulation after registering the email
        
        # Mock Flask request context
        with app.test_client() as client: #test_client allow to send a request to the app - response = client.post
            with app.app_context():
                with patch('app.Validators.validate_registration_data',mock_validate):
                    with patch('app.get_db_connection',mock_db):
                        with patch('app.generate_password_hash',mock_hash):
                            response = client.post(
                                '/register',
                                json={"email": "test@example.com", "password": "RawPass123@"},
                                content_type='application/json'
                            )

                            assert response.status_code == 201
                            response_data = response.get_json()
                            assert response_data["user_id"] == 456
                            assert response_data["email"] == "test@example.com"

                            mock_validate.assert_called_once_with({"email": "test@example.com", "password": "RawPass123@"})
                                   

    @patch('app.Validators.validate_registration_data')
    def test_register_route_validation_failure(self, mock_validate):
        """Test /register route with invalid data"""
        # Configure validation to fail
        mock_validate.return_value = (False, {
            "error": "Invalid email: email format invalid"
        })
        
        with app.test_client() as client:
            with app.app_context():
                with patch('app.Validators.validate_registration_data', mock_validate):
                    response = client.post(
                        '/register',
                        json={"email": "bad-email", "password": "pass"},
                        content_type='application/json'
                    )

                    assert response.status_code == 400
                    response_data = response.get_json()
                    assert "error" in response_data
                    assert "email" in response_data["error"].lower()
    
    @patch('app.get_db_connection')
    @patch('app.check_password_hash')
    def test_login_route_success(self, mock_check_hash, mock_db):

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_conn
        mock_cursor.fetchone.return_value = {
            'id': 123,
            'email': 'test@example.com',
            'password': 'hashed_password'
        }
        mock_check_hash.return_value = True

        with app.test_client() as client:
            with app.app_context():
                with patch('app.get_db_connection', mock_db):
                    with patch('app.check_password_hash', mock_check_hash):
                        with patch('app.jwt.encode') as mock_jwt_encode:
                            mock_jwt_encode.return_value = 'mock.jwt.token'
                            response = client.post(
                                '/login',
                                json={"email": "test@example.com", "password": "Password123@"},
                                content_type='application/json')
                            assert response.status_code == 200
                            response_data = response.get_json()
                            assert "token" in response_data
                            assert response_data["token"] == 'mock.jwt.token'
                            assert response_data["user_id"] == 123

    @patch('app.get_db_connection')
    @patch('app.jwt.decode')
    def test_get_profile_route(self,mock_jwt_decode, mock_db):
        
        mock_jwt_decode.return_value = {'user_id': 123, 'email': 'test@example.com'}
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_conn
        mock_cursor.fetchone.return_value = {'id':123, 'email':'test@example.com'}

        with app.test_client() as client:
            with app.app_context():
                with patch('app.get_db_connection', mock_db):
                    with patch('app.jwt.decode', mock_jwt_decode):

                        response = client.get(
                            '/profile',
                            headers={'Authorization': 'Bearer valid.jwt.token'}
                        )

                        assert response.status_code == 200
                        response_data = response.get_json()
                        assert response_data["user_id"] == 123
                        assert response_data["email"] == "test@example.com"
    
    @patch('app.get_db_connection')
    @patch('app.jwt.decode')
    def test_get_profile_by_id_route(self,mock_jwt_decode, mock_db):
        
        mock_jwt_decode.return_value = {'user_id': 123, 'email': 'test@example.com'}

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_conn
        mock_cursor.fetchone.return_value = {'id':123, 'email':'test@example.com'}

        with app.test_client() as client:
            with app.app_context():
                with patch('app.get_db_connection', mock_db):
                    with patch('app.jwt.decode', mock_jwt_decode):

                        response = client.get(
                            '/users/123',
                            headers={'Authorization': 'Bearer valid.jwt.token'}
                        )

                        assert response.status_code == 200
                        response_data = response.get_json()
                        assert response_data["user_id"] == 123
                        assert response_data["email"] == "test@example.com"

    @patch('app.get_db_connection')
    @patch('app.jwt.decode')
    def test_get_profile_by_id_unauthorized(self,mock_jwt_decode, mock_db):
        
        mock_jwt_decode.return_value = {'user_id': 123, 'email': 'test@example.com'}
        #No need to configure mock_cursor since the unauthorized access happens before any db interaction


        with app.test_client() as client:
            with app.app_context(): #No need to configure the mock_db since the unauthorized access happens before any db interaction
                    with patch('app.jwt.decode', mock_jwt_decode):

                        response = client.get(
                            '/users/999', # trying to access another user's profile
                            headers={'Authorization': 'Bearer valid.jwt.token'}
                        )

                        assert response.status_code == 403
                        response_data = response.get_json()
                        assert "Unauthorized access" in response_data["error"]
                        mock_db.assert_not_called()  # Ensure DB was not accessed

    @patch('app.get_db_connection')
    @patch('app.jwt.decode')
    def test_get_profile_route_user_id_not_found(self,mock_jwt_decode, mock_db):
        
        mock_jwt_decode.return_value = {'user_id': 123, 'email': 'test@example.com'}
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_conn
        mock_cursor.fetchone.return_value = None

        with app.test_client() as client:
            with app.app_context():
                with patch('app.get_db_connection', mock_db):
                    with patch('app.jwt.decode', mock_jwt_decode):

                        response = client.get(
                            '/users/123',
                            headers={'Authorization': 'Bearer valid.jwt.token'}
                        )

                        assert response.status_code == 404
                        response_data = response.get_json()
                        assert "User not found" in response_data["error"]


    @patch('app.Validators.validate_email')
    @patch('app.Validators.validate_password')
    @patch('app.get_db_connection')
    @patch('app.jwt.decode')
    def test_update_route_success(self, mock_jwt_decode, mock_db, mock_validate_password, mock_validate_email):

        mock_jwt_decode.return_value = {'user_id': 123, 'email': 'test@example.com'}
        mock_validate_email.return_value = (True, "update@example.com")
        mock_validate_password.return_value = (True, "NewPass@123")

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_conn

        with app.test_client() as client:
            with app.app_context():
                with patch('app.get_db_connection', mock_db):
                    with patch('app.jwt.decode', mock_jwt_decode):

                        response = client.put(
                        '/profile',
                        json={"email": "update@example.com", 
                            "password": "NewPass@123"
                    },
                    headers={'Authorization': 'Bearer valid.jwt.token'},
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                response_data = response.get_json()
                assert "Profile updated successfully" in response_data["message"]
                assert mock_cursor.execute.call_count == 2  # One for email, one for password update
    
    @patch('app.jwt.decode')
    def test_logout_route_success(self, mock_jwt_decode):
        """Test logout route"""

        mock_jwt_decode.return_value = {'user_id': 123, 'email': 'test@example.com','exp':1234567890}

        token_blacklist.clear()
        blacklist_expiry.clear()

        with app.test_client() as client:
            with app.app_context():
                with patch('app.jwt.decode', mock_jwt_decode):

                    response = client.post(
                        '/logout',
                        headers={'Authorization': 'Bearer valid.jwt.token'}
                    )

                    assert response.status_code == 200
                    response_data = response.get_json()
                    assert "Logout successful" in response_data["message"]
                    assert response_data["user_id"] == 123
                    
                    # Verify token was added to blacklist
                    assert "valid.jwt.token" in token_blacklist
                    assert "valid.jwt.token" in blacklist_expiry
    

    def test_logout_without_token(self):
        with app.test_client() as client:
            response = client.post('/logout')
            
            assert response.status_code == 401
            response_data = response.get_json()
            assert "Authorization header is missing" in response_data["error"]


class TestHealthEndpoints:
    
    @patch('app.get_db_connection')
    def test_health_check(self, mock_db):
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        
        with app.test_client() as client:
            response = client.get('/health')
            assert response.status_code == 200
            assert response.get_json()["status"] == "healthy"
    
    @patch('app.get_db_connection')
    def test_health_check_detailed(self, mock_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_conn
        
        with app.test_client() as client:
            response = client.get('/health/detailed')
            assert response.status_code == 200
            data = response.get_json()
            assert "checks" in data
            assert data["checks"]["database_connection"] == True
            assert data["checks"]["database_query"] == True
    
    def test_metrics_endpoint(self):
        with app.test_client() as client:
            response = client.get('/metrics')
            assert response.status_code == 200
            data = response.get_json()
            assert "service" in data
            assert data["service"] == "user-service"
            assert "active_endpoints" in data


if __name__ == "__main__":
    # to run tests in this file directly
    pytest.main([__file__, "-v"])
