import jwt,datetime,os,pymysql,logging, time;
from functools import wraps
from flask import Flask, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from pymysql import Error
from dotenv import dotenv_values
from pathlib import Path
from product_validator import ProductValidator

def get_port():
    port = os.environ.get('FLASK_RUN_PORT','3002')
    return int(port)

def get_debug_mode():
    env = os.environ.get('FLASK_ENV', 'development')
    return env in ['development', 'staging']


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
app.config["MYSQL_HOST"] = os.environ.get("MYSQL_HOST") or os.environ.get("PRODUCT_MYSQL_HOST") 
app.config["MYSQL_USER"] = os.environ.get("MYSQL_USER") or os.environ.get("PRODUCT_MYSQL_USER")
app.config["MYSQL_PASSWORD"] = os.environ.get("MYSQL_PASSWORD") or os.environ.get("PRODUCT_MYSQL_PASSWORD")
app.config["MYSQL_DB"] = os.environ.get("MYSQL_DATABASE") or os.environ.get("PRODUCT_MYSQL_DB")
app.config["MYSQL_PORT"] = os.environ.get("MYSQL_PORT") or os.environ.get("PRODUCT_MYSQL_PORT")

def setup_structured_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "product-service", "message": "%(message)s"}',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
setup_structured_logging()


def get_db_connection():
    try:
        connection = pymysql.connect(
            host=app.config["MYSQL_HOST"],
            user=app.config["MYSQL_USER"],
            password=app.config["MYSQL_PASSWORD"],
            db=app.config["MYSQL_DB"],
            port=int(app.config["MYSQL_PORT"]),
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Error as e:
        logging.error(f"Error connecting to products database: {e}")
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


@app.route("/products", methods=["POST"])
@token_required
def create_product(current_user_id):
    data = request.get_json()
    logging.info("product creation request received", extra={"product_name" : data.get("name"),"price":data.get("price") if data else "No data"})
    
    is_valid, validation_response = ProductValidator.validate_registration_object(data)
    if not is_valid:
        logging.warning(f"Product registration failed:{validation_response}")
        return jsonify(validation_response), 400
    
    name = validation_response["product_name"]
    price = validation_response["price"]
    quantity = validation_response.get("quantity",0)
    description = validation_response.get("description","")

    connection = get_db_connection()
    if not connection:
        logging.error("Database connection failed during product creation")
        return jsonify({"error": "Database connection failed"}), 500    

    try:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO items (name, price,quantity, description, created_by) VALUES (%s, %s, %s, %s, %s)",
                           (name, price, quantity, description, current_user_id))
            
            id = cursor.lastrowid
            connection.commit()
            logging.info("Product created", extra ={"product_id": id, "product_name": name})
            return jsonify({"message": "Product created successfully", 
                            "id": id,
                            "product_name":name,
                            "description": description,
                            "quantity": quantity,
                            "price": price
                            }), 201
        
    except Error as e:
        logging.error("Product creation error:", extra={"error": str(e)})
        return jsonify({"error": "Failed to create product"}), 500
    
    finally:
        connection.close()


@app.route("/products", methods=["GET"])
@token_required
def get_products(current_user_id):
    token = request.headers.get('Authorization')
    if token and token.startswith("Bearer "):
        token = token[7:]
    data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
    user_email = data['email']
    logging.info("product list request received", extra={"user_id": current_user_id, "user_email":user_email})

    connection = get_db_connection()
    if not connection:
        logging.error("Database connection failed")
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, name, price, quantity, description, created_at, created_by FROM items WHERE created_by = %s",(current_user_id,))
            products = cursor.fetchall()

            #Json doesn't accept Decimal types, convert to float
            for product in products:
                if 'price' in product and product['price'] is not None:
                    product['price'] = float(product['price'])

            if not products:
                logging.info("No products_found", extra={"user_id": current_user_id})
                return jsonify({"message": "No products found", "products": []}), 200
            
            logging.info(f"Products retrieved:{len(products)}", extra={"user_id": current_user_id, "product_count": len(products)})
            return jsonify({"products": products}), 200
        
    except Error as e:
        logging.error("Error retrieving products", extra={"error": str(e)})
        return jsonify({"error": "Failed to retrieve products"}), 500
    
    finally:
        connection.close()


@app.route("/products", methods=["PUT"])
@token_required
def update_product(current_user_id):
    data = request.json
    logging.info("Product update request received", extra={"product_id": data.get("id"),"product_name": data.get("name") if data else "No data"})

    if not data or not data.get("id"):
        logging.warning("Product update failed - missing item ID")
        return jsonify({"error": "Product ID of the item to be changed is required",
                        "example request":{"id":"1",
                                           "name":"New Product Name",
                                           "price": "19.99",
                                           "description": "Updated description",
                                           "quantity":"5"
                                           }
                      }), 400
    
    target_id = data["id"]
    new_product_name = data.get("name")
    new_price = data.get("price")
    new_quantity = data.get("quantity")
    new_description = data.get("description")

    if new_product_name:
        is_valid_name, name_result = ProductValidator.validate_product(new_product_name)
        if not is_valid_name:
            logging.warning("Product name update failed - invalid product name", extra={"user_id": current_user_id, "product name": new_product_name})
            return jsonify({"error":f"Invalid product name: {name_result}"}), 400
        new_product_name = ProductValidator.sanitize_input(new_product_name).lower()
    
    if new_price:
        is_valid_price, price_result = ProductValidator.validate_product_price(new_price)
        if not is_valid_price:
            logging.warning("Product price update failed - invalid price", extra={"user_id": current_user_id, "product price": new_price})
            return jsonify({"error":f"Invalid price: {price_result}"}), 400
    
    if new_quantity:
        is_valid_quantity, quantity_result = ProductValidator.validate_product_quantity(new_quantity)
        if not is_valid_quantity:
            logging.warning("Product quantity update failed - invalid quantity", extra={"user_id": current_user_id, "product quantity": new_quantity})
            return jsonify({"error":f"Invalid quantity: {quantity_result}"}), 400
        
    if new_description:
        is_valid_description, description_result = ProductValidator.validate_product_description(new_description)
        if not is_valid_description:
            logging.warning("Product description update failed - invalid description", extra={"user_id": current_user_id, "product description": new_description})
            return jsonify({"error":f"Invalid quantity: {description_result}"}), 400
        new_description = ProductValidator.sanitize_input(description_result)


    connection = get_db_connection()

    if not connection:
        logging.error("Database connection failed during producto update")
        return jsonify({"Error": "Database connection failed"}), 500
    
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM items WHERE id = %s AND created_by = %s",(target_id,current_user_id))
            selected_product = cursor.fetchone()
            if not selected_product:
                return jsonify({"error":"product not found or access denied"}),404

            if new_product_name is not None:# Allow empty name
                cursor.execute("UPDATE items SET name = %s WHERE id = %s AND created_by = %s",(new_product_name, target_id, current_user_id))

            if new_price is not None:# Allow zero price check above
                cursor.execute("UPDATE items SET price = %s WHERE id = %s AND created_by = %s",(new_price, target_id, current_user_id))
                
            if new_description is not None:# Allow empty description
                cursor.execute("UPDATE items SET description = %s WHERE id = %s AND created_by = %s",(new_description, target_id, current_user_id))

            if new_quantity is not None:# Allow zero quantity
                cursor.execute("UPDATE items SET quantity = %s WHERE id = %s AND created_by = %s",(new_quantity, target_id, current_user_id))
                
            connection.commit()

            logging.info("Product updated succesfully", extra={"product_id":target_id})
            return jsonify({"message":"Product updated successfully"}), 200
    
    except Error as e:
        logging.error("Error updating product", extra={"error": str(e), "product_id": target_id})
        return jsonify({"error": "Failed to update product"}), 500
    
    finally:
        connection.close()


@app.route("/products", methods=["DELETE"])
@token_required
def delete_product(current_user_id):
    data = request.get_json()
    logging.info("Product deletion request received", extra={"product_id": data.get("id") if data else "No data"})

    if not data or not data.get("id"):
        logging.warning("Product deletion failed - missing item ID")
        return jsonify({"error": "Product ID of the item to be deleted required",
                        "example request":{"id":"1"}
                        })
    
    target_id = data["id"]
    connection = get_db_connection()

    if not connection:
        logging.error("Database connection failed during product deletion")
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM items WHERE id = %s AND created_by =%s",(target_id, current_user_id))
            product = cursor.fetchone()
            if not product:
                logging.warning("Product deletion failed - product not found", extra={"product_id": target_id})
                return jsonify({"error": "Product not found"}), 404

            cursor.execute("DELETE FROM items WHERE id = %s AND created_by = %s",(target_id, current_user_id))
            connection.commit()
            
            #verification to see how many lines were deleted
            if cursor.rowcount > 0:
                logging.info("Product deleted successfully", extra={"product_id":target_id,"product_name":product["name"]})
                return jsonify({"message": "Product deleted successfully",
                                "deleted_product_id":target_id
                                }), 200
            else:
                logging.warning("No product was deleted", extra={"product_id":target_id, "user_id":current_user_id})
                return jsonify({"error":"No product was deleted"}),404
    
    except Error as e:
        logging.error("Error deleting product", extra={"error":str(e), "product_id":target_id, "user_id":current_user_id})
        connection.rollback()
        return jsonify({"error": "Failed to delete product"}),500
    
    finally:
        connection.close()


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
                    "service": "product-service", 
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "checks": checks
                        
                    }), 200 if all_healthy else 503


@app.route("/metrics",methods=["GET"])
def metrics():
    return jsonify({
        "service": "user-service",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "active_endpoints": ["/product", "/health","health/detailed", "/metrics"]
    })


def verify_db_setup():
    max_retries = 15
    retry_delay = 5  # seconds

    for attempt in range(1, max_retries + 1):
        connection = None
        try: #Verify basic connectivity
            connection = get_db_connection()
            if not connection:
                print(f"Database connection returned none, attempt: {attempt}")
                raise Exception("Connection returned None")
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                print(f"Database connection established on attempt: {attempt}")
                
                if not result:
                    raise Exception("Simple query 1 failed")
            
            print (f"Basic connectivity successful, attempt: {attempt}")

            try:# Verify 'items' existence
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) as table_exists
                        FROM information_schema.tables
                        WHERE table_schema = DATABASE()
                        AND table_name = 'items'
                        """)
                    result = cursor.fetchone()

                    if result['table_exists'] > 0:
                        cursor.execute("SELECT COUNT(*) AS count FROM items")
                        product_result = cursor.fetchone()
                        product_count = product_result['count']
                        print(f"tabel 'items' exists with {product_count} records")
                    else:
                        print("table 'items' still not exists")
                    
            except Exception as e:
                print(f"Table verification failed: {e}")
            
            finally:
                if connection:
                    try:
                        connection.close()
                    except Exception as close_err:
                        print(f"Failed to close connection: {close_err}")

            return True

        except Exception as e:
            print(f"Database setup verification attempt: {attempt} failed with error: {e}")

            if attempt < max_retries:
                print(f"attempt: {attempt} failed, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Database setup verification failed")
                return False
    return False        

if __name__ == "__main__":
    port = get_port()
    debug_mode = get_debug_mode()
    environment = os.environ.get('FLASK_ENV','development')

    print("=" * 50)
    print(f"Starting Product Service - Environment: {environment}")
    print(f"Port: {port}")
    print(f"Debug mode: {debug_mode}")
    print("=" * 50)
    
    print("Available endpoints:")
    print("  POST  /products     - Register new products")
    print("  GET   /products     - Get products list (JWT required)") 
    print("  PUT   /products     - Update products (JWT required)")
    print(" DELETE /products     - Delete product (JWT required)")
    print("  GET   /health       - Health check")
    print("  GET   /health/detailed - Detailed health check")
    print("  GET   /metrics      - Service metrics")
    print("=" * 50)

    if verify_db_setup():
        app.run(host="0.0.0.0",port=port,debug=debug_mode)
    else:
        print("Failed to start Product Service due to database setup issues.")
    