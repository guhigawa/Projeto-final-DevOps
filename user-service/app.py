import jwt,datetime,os,pymysql,logging, time;
from functools import wraps
from flask import Flask, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from pymysql import Error
from dotenv import dotenv_values
from pathlib import Path

def load_env_files():
    current_dir = Path(__file__).parent

    env_test_path = current_dir.parent / '.env.test'
    if env_test_path.exists():
        env_vars= dotenv_values(str(env_test_path))
        for key, values in env_vars.items():
            os.environ[key] = values
        return
    
    root_env_path = current_dir.parent / '.env'
    if root_env_path.exists():
        env_vars = dotenv_values(str(root_env_path))
        for key, values in env_vars.items():
            os.environ[key] = values
        return

load_env_files()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
token_blacklist = set()
blacklist_expiry = {}

#config
app.config["MYSQL_HOST"] = os.environ.get("MYSQL_HOST") or os.environ.get("USER_MYSQL_HOST")
app.config["MYSQL_USER"] = os.environ.get("MYSQL_USER") or os.environ.get("USER_MYSQL_USER")
app.config["MYSQL_PASSWORD"] = os.environ.get("MYSQL_PASSWORD") or os.environ.get("USER_MYSQL_PASSWORD")
app.config["MYSQL_DB"] = os.environ.get("MYSQL_DATABASE") or os.environ.get("USER_MYSQL_DB")
app.config["MYSQL_PORT"] = os.environ.get("MYSQL_PORT") or os.environ.get("USER_MYSQL_PORT")

#logging setup
def setup_structured_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "user-service", "message": "%(message)s"}',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
setup_structured_logging()

def get_db_connection():
    try:
        connection = pymysql.connect(
            host=app.config["MYSQL_HOST"],
            user=app.config["MYSQL_USER"],
            password=app.config["MYSQL_PASSWORD"],
            database=app.config["MYSQL_DB"],
            port=int(app.config["MYSQL_PORT"]),
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Error as e:
        logging.error(f"Error connecting to MySQL Platform: {e}")
        return None

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing!"}), 401
        
        try:
            if token.startswith("Bearer "):
                token = token[7:]

                data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
                current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token!"}), 401
        

        return f(current_user_id, *args, **kwargs)
    return decorated

@app.before_request
def check_blacklisted_token():
    
    cleanup_expired_tokens()

    # Public routes that do not require token validation
    public_routes = ['/login', '/register', '/health', '/health/detailed', '/metrics']
    
    if request.path in public_routes:
        return
    
    # Protected routes - check for blacklisted token
    auth_header = request.headers.get('Authorization')
    
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        
        if token in token_blacklist:
            logging.warning("Access attempt with blacklisted token", 
                          extra={"endpoint": request.path, "method": request.method})
            return jsonify({
                "error": "Token has been invalidated. Please login again."
            }), 401
    

# Function to clean up expired tokens from the blacklist
def cleanup_expired_tokens():
    
    current_time = time.time()
    tokens_to_remove = []
    
    for token, exp_time in blacklist_expiry.items():
        if exp_time < current_time:
            tokens_to_remove.append(token)
    
    for token in tokens_to_remove:
        token_blacklist.discard(token)
        blacklist_expiry.pop(token, None)
    
    if tokens_to_remove:
        logging.info(f"Cleaned up {len(tokens_to_remove)} expired tokens from blacklist")

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    logging.info("Registration attempt", extra={"email": data.get("email") if data else "No data"})

    if not data or not data.get("email") or not data.get("password"):
        logging.warning("Registration failed - missing fields")
        return jsonify({"error": "Email and password are required",
        "example_request": {"email":"userexample@email.com",
                            "password":"securepassword123"
                            }
                        }), 400 #400 = Bad Request(missing or invalid data)
    
    email = data["email"]
    password = data["password"] 

    connection = get_db_connection()
    if not connection:
        logging.error("Database connection error during registration")
        return jsonify({"error": "Database connection error"}), 503 #503 = Service Unavailable(database down or unreachable)
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email=%s",(email,))
            existing_user = cursor.fetchone()

            if existing_user:
                logging.warning("Registration failed - user already exists", extra={"email": email})
                return jsonify({"error": "User already exists"}), 409 #409 = Conflict(user already exists)
            
            hashed_password = generate_password_hash(password)
            cursor.execute("INSERT INTO users (email, password) VALUES (%s, %s)",(email, hashed_password))
            user_id = cursor.lastrowid
            connection.commit()

            logging.info("User registered successfully", extra={"email": email, "user_id": user_id})

            return jsonify({
                "message": "User registered successfully",
                "user_id": user_id,
                "email": email
            }), 201 #201 = Created(resource successfully created)

    except Exception as e:
        logging.error(f"Registration error", extra={"email": email, "error": str(e)})
        return jsonify({"error": f"Registration error: {str(e)}"}), 500 #
    finally:
        connection.close()

@app.route("/login", methods=["POST"])
def login():
    auth = request.authorization
    data = {}
    
    #check db for username and password
    #determining the authentication method
    if auth and auth.username and auth.password:
        user_email = auth.username
        password = auth.password
        auth_method = "basic"

    elif request.is_json:
        try:
            data = request.get_json()
            if data.get("email") and data.get("password"):
                user_email = data.get("email")
                password = data.get("password","")
                auth_method = "json"
            else:
                logging.warning("No valid authentication method provided")
                return jsonify({
                    "error": "No valid authentication method provided", 
                    "supported_auth_methods": ["basic_auth","json"]}), 400 #400 = Bad Request(no valid authentication method)
        except Exception as e:
            logging.error(f"Error parsing JSON data during login", extra={"error": str(e)})
            return jsonify({
                "error": "Invalid JSON data", 
                "supported_auth_methods": ["basic_auth","json"]}), 400 #400 = Bad Request(invalid JSON data)
    else:
        logging.warning("No valid authentication method provided")
        return jsonify({
            "error": "No valid authentication method provided", 
            "supported_auth_methods": ["basic_auth","json"]}), 400 #400 = Bad Request(no valid authentication method)
    
    logging.info("Login attempt", extra={"email": user_email, "auth_method": auth_method})

    if not user_email or not password:
        logging.warning("Login failed - missing credentials")
        return jsonify({
            "error": "Missing credentials", 
            "supported_auth_methods": ["basic_auth","json"]}), 401 #401 = Unauthorized(missing or invalid credentials)
    
    #logic for authentication
    connection = get_db_connection()
    if not connection:
        logging.error("Database connection error during login")
        return jsonify({"error": "Database connection error"}), 503 #503 = Service Unavailable(database down or unreachable)
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email=%s",(user_email,))
            user=cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            token = jwt.encode({
                "user_id": user['id'],
                "email": user['email'],
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            }, app.config['SECRET_KEY'], algorithm="HS256")

            logging.info("User logged in successfully", extra={"email": user_email, "user_id": user['id']})
            
            return jsonify({
                "token": token,
                "user_id": user['id'],
                "email": user['email']
                })
        else:
            logging.warning("Login failed - invalid credentials", extra={"email": user_email})
            return jsonify({"error": "Invalid credentials"}), 401
        
    except Exception as e:
        logging.error(f"Authentication error", extra={"email": user_email, "error": str(e)})
        return jsonify({"error": f"Authentication error: {e}"}), 500
    finally:
        connection.close()

@app.route("/profile", methods=["GET"])
@token_required
def get_profile(current_user_id):
    connection = get_db_connection()
    if not connection:
        logging.error("Database connection error during profile retrieval")
        return jsonify({"error": "Database connection error"}), 503 #503 = Service Unavailable(database down or unreachable)
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, email FROM users WHERE id=%s",(current_user_id,))
            user = cursor.fetchone()

        if not user:
            logging.warning("Profile retrieval failed - user not found", extra={"user_id": current_user_id})
            return jsonify({"error": "User not found"}), 404 #404 = Not Found(user does not exist)
        
        logging.info("Profile retrieved successfully", extra={"user_id": current_user_id})
        return jsonify({
            "user_id": user['id'],
            "email": user['email']
        })

    except Exception as e:
        logging.error(f"Profile retrieval error", extra={"user_id": current_user_id, "error": str(e)})
        return jsonify({"error": f"Profile retrieval error:{str(e)}"}), 500
    finally:
        connection.close()

@app.route("/profile", methods=["PUT"])
@token_required
def update_profile(current_user_id):
    data = request.get_json()

    if not data:
        logging.warning("Profile update failed - no data provided", extra={"user_id": current_user_id})
        return jsonify({"error": "No data provided"}), 400

    email = data.get("email")
    password = data.get("password")

    if not email and not password:
        logging.warning("Profile update failed - no fields to update", extra={"user_id": current_user_id})
        return jsonify({"error": "At least one field (email or password) must be provided"}), 400

    connection = get_db_connection()

    if not connection:
        logging.error("Database connection error during profile update")
        return jsonify({"error": "Database connection error"}), 503 #503 = Service Unavailable(database down or unreachable)
    
    try:
        with connection.cursor() as cursor:
            if email:
                cursor.execute("UPDATE users SET email=%s WHERE id=%s",(email, current_user_id))
            if password:
                hashed_password = generate_password_hash(password)
                cursor.execute("UPDATE users SET password=%s WHERE id=%s",(hashed_password, current_user_id))
            
            connection.commit()

        logging.info("Profile updated successfully", extra={"user_id": current_user_id})
        return jsonify({"message": "Profile updated successfully"})

    except Exception as e:
        logging.error(f"Profile update error", extra={"user_id": current_user_id, "error": str(e)})
        return jsonify({"error": f"Profile update error: {str(e)}"}), 500
    finally:
        connection.close()

@app.route("/users/<int:user_id>", methods=["GET"])
@token_required
def get_user_by_id(current_user_id, user_id):
    if current_user_id != user_id:
        logging.warning("Unauthorized access attempt to user data", extra={"requested_user_id": user_id, "current_user_id": current_user_id})
        return jsonify({"error": "Unauthorized access"}), 403 #403 = Forbidden(trying to access resources they do not own)

    connection = get_db_connection()
    if not connection:
        logging.error("Database connection error during user retrieval by ID")
        return jsonify({"error": "Database connection error"}), 503 #503 = Service Unavailable(database down or unreachable)
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, email FROM users WHERE id=%s",(user_id,))
            user = cursor.fetchone()

        if not user:
            logging.warning("User retrieval by ID failed - user not found", extra={"requested_user_id": user_id, "current_user_id": current_user_id})
            return jsonify({"error": "User not found"}), 404 #404 = Not Found(user does not exist)
        
        logging.info("User retrieved by ID successfully", extra={"requested_user_id": user_id, "current_user_id": current_user_id})
        return jsonify({
            "user_id": user['id'],
            "email": user['email']
        })

    except Exception as e:
        logging.error(f"User retrieval by ID error", extra={"requested_user_id": user_id, "current_user_id": current_user_id, "error": str(e)})
        return jsonify({"error": f"User retrieval error:{str(e)}"}), 500
    finally:
        connection.close()

@app.route("/logout", methods=["POST"])
def logout():
    """"Endpoint for logout - invalidating JWT token, requires Header Authorization with Bearer token"""

    #Getting authorization header
    auth_header = request.headers.get('Authorization')
    
    #validating toke presence
    if not auth_header:
        logging.warning("Logout attempt without authorization header")
        return jsonify({"error": "Authorization header is missing"}), 401 #401 = Unauthorized

    if not auth_header.startswith("Bearer "):
        logging.warning("Logout attempt with invalid authorization format")
        return jsonify({"error": "Bearer toke required"}), 401 #401 = Unauthorized
    
    #Extracting token
    token = auth_header.split(" ")[1]

    try:
        #Decoding token to get expiration time
        decoded_token = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        
        user_id = decoded_token.get("user_id")
        email = decoded_token.get("email")
        exp = decoded_token.get("exp")

        token_blacklist.add(token)

        if exp:
            blacklist_expiry[token] = exp

        logging.info("User logged out successfully", extra={"user_id": user_id, 
                                                            "email": email
                                                            })
        return jsonify({"message": "Logout successful",
                        "user_id": user_id,
                        "timestamp": datetime.datetime.utcnow().isoformat()
                        }), 200
    except jwt.ExpiredSignatureError:
        logging.warning("Logout attempt with expired token")
        return jsonify({"error": "Token has already expired"}), 401 #401 = Unauthorized
    except jwt.InvalidTokenError:
        logging.warning("Logout attempt with invalid token")
        return jsonify({"error": "Invalid token"}), 401 #401 = Unauthorized


#Health check endpoint
@app.route("/health", methods=["GET"])
def health_check():
    try:
        connection = get_db_connection()
        healthy = connection is not None
        if connection:
            connection.close()
        return jsonify({"status": "healthy" if healthy else "unhealthy"})
    except:
        return jsonify({"status": "unhealthy"}), 503

@app.route("/health/detailed",methods=["GET"])
def health_detailed():
    checks = {
        "database_connection": False,
        "database_query":False,
        "service_responsive":True
    }

    try:
        connection = get_db_connection()
        if connection:
            checks["database_connection"] = True
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
                checks["database_query"] = True
            connection.close()
    
    except Exception as e:
        logging.error(f"Health check error: {str(e)}")

    all_healthy = all(checks.values())
    status = "healthy" if all_healthy else "unhealthy"

    logging.info(f"Health check executed - Status: {status}", extra={"checks": checks})

    return jsonify({"status": status,
                    "service": "user-service", 
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "checks": checks
                        
                    }), 200 if all_healthy else 503

@app.route("/metrics",methods=["GET"])
def metrics():
    return jsonify({
        "service": "user-service",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "active_endpoints": ["/register", "/login", "/profile", "/users/<id>", "/health", "/metrics"]
    })


def verify_db_setup():
    try:
        connection = get_db_connection()
        if not connection:
            print(f"Failed to connect to database")
            return False
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS count FROM users")
            result = cursor.fetchone()
            user_count = result['count'] 

            print(f"table users exists and has {user_count} users")
        
        connection.close()
        return True
    
    except Exception as e:
        print(f"Database setup verification failed: {e}")
        return False


if __name__ == "__main__":
    print("Starting User Service...")
    print("Available endpoints:")
    print("  POST /register     - Register new user")
    print("  POST /login        - Login user") 
    print("  GET  /profile      - Get user profile (JWT required)")
    print("  PUT  /profile      - Update profile (JWT required)")
    print("  GET  /health       - Health check")
    print("  GET  /health/detailed - Detailed health check")
    print("  GET  /metrics      - Service metrics")

    if verify_db_setup():
        app.run(host="0.0.0.0",port=3001,debug=True)
    else:
        print("Failed to start User Service due to database setup issues.")