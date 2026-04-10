import jwt,datetime,os,pymysql,logging, time;
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from pymysql import Error
from dotenv import dotenv_values
from pathlib import Path
from product_validator import ProductValidator
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.pymysql import PyMySQLInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.trace import Status, StatusCode

def setup_tracing():
    resource = Resource.create({
        SERVICE_NAME: "product-service",
        "deployment.environment": os.environ.get('FLASK_ENV', 'development'),
        "service.version": "1.0.0"
        })
    
    provider = TracerProvider(resource=resource)

    jaeger_exporter = JaegerExporter(
        agent_host_name=os.environ.get('JAEGER_AGENT_HOST', 'jaeger.monitoring.svc.cluster.local'),
        agent_port=int(os.environ.get('JAEGER_AGENT_PORT', '6831')),
    )
    span_processor = BatchSpanProcessor(jaeger_exporter)
    provider.add_span_processor(span_processor)

    trace.set_tracer_provider(provider)

    FlaskInstrumentor().instrument_app(app)
    RequestsInstrumentor().instrument()
    PyMySQLInstrumentor().instrument()
    LoggingInstrumentor().instrument()
    
    return trace.get_tracer(__name__)

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
tracer = setup_tracing()
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
    with tracer.start_as_current_span("create_product") as span:
        data = request.get_json()
        span.set_attribute("http.method", "POST")
        span.set_attribute("http.route", "/products")
        span.set_attribute("user_id", current_user_id)
        logging.info("product creation request received", extra={"product_name" : data.get("name"),"price":data.get("price") if data else "No data"})
    
    is_valid, validation_response = ProductValidator.validate_registration_object(data)
    if not is_valid:
        span.set_attribute("error", True)
        span.set_attribute("error.message", validation_response.get("error", "Invalid data"))
        logging.warning(f"Product registration failed:{validation_response}")
        return jsonify(validation_response), 400
    
    name = validation_response["product_name"]
    price = validation_response["price"]
    quantity = validation_response.get("quantity",0)
    description = validation_response.get("description","")

    span.set_attribute("product.name", name)
    span.set_attribute("product.price", price)
    span.set_attribute("product.quantity", quantity)
    span.set_attribute("product.description", description)

    connection = get_db_connection()
    if not connection:
        logging.error("Database connection failed during product creation")
        span.set_attribute("error", True)
        span.set_attribute("error.message", "Database connection failed")
        span.set_status(Status(StatusCode.ERROR, "Database connection failed"))
        return jsonify({"error": "Database connection failed"}), 500    

    try:
        with connection.cursor() as cursor:
            with tracer.start_as_current_span("insert_product") as insert_span:
                cursor.execute("INSERT INTO items (name, price,quantity, description, created_by) VALUES (%s, %s, %s, %s, %s)",
                            (name, price, quantity, description, current_user_id))
                
                id = cursor.lastrowid
                connection.commit()
                insert_span.set_attribute("product.id", id)
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
        span.set_attribute("error", True)
        span.set_attribute("error.message", str(e))
        span.set_status(Status(StatusCode.ERROR, str(e)))
        return jsonify({"error": "Failed to create product"}), 500
    
    finally:
        connection.close()


@app.route("/products", methods=["GET"])
@token_required
def get_products(current_user_id):
    with tracer.start_as_current_span("get_product") as span:
        span.set_attribute("http.method", "GET")
        span.set_attribute("http.route", "/prdoducts")
        span.set_attribute("user_id", current_user_id)
        token = request.headers.get('Authorization')
        if token and token.startswith("Bearer "):
            token = token[7:]
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        user_email = data['email']
        span.set_attribute("user_email", user_email)
        logging.info("product list request received", extra={"user_id": current_user_id, "user_email":user_email})

        connection = get_db_connection()
        if not connection:
            logging.error("Database connection failed")
            span.set_attribute("error", True)
            span.set_attribute("error.message", "Database connection failed")
            span.set_status(Status(StatusCode.ERROR, "Database connection failed"))
            return jsonify({"error": "Database connection failed"}), 500
    
        try:
            with connection.cursor() as cursor:
                with tracer.start_as_current_span("query_product") as query_span:
                    cursor.execute("SELECT id, name, price, quantity, description, created_at, created_by FROM items WHERE created_by = %s",(current_user_id,))
                    products = cursor.fetchall()
                    query_span.set_attribute("product.count", len(products))

                    #Json doesn't accept Decimal types, convert to float
                    for product in products:
                        if 'price' in product and product['price'] is not None:
                            product['price'] = float(product['price'])

                    if not products:
                        logging.info("No products_found", extra={"user_id": current_user_id})
                        query_span.set_attribute("empty_query", True)
                        span.set_attribute("product_found", False)
                        return jsonify({"message": "No products found", "products": []}), 200
                    
                logging.info(f"Products retrieved:{len(products)}", extra={"user_id": current_user_id, "product_count": len(products)})
                span.set_attribute("product_found", True)
                return jsonify({"products": products}), 200
            
        except Error as e:
            logging.error("Error retrieving products", extra={"error": str(e)})
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            span.set_status(Status(StatusCode.ERROR, str(e)))
            return jsonify({"error": "Failed to retrieve products"}), 500
        
        finally:
            connection.close()


@app.route("/products", methods=["PUT"])
@token_required
def update_product(current_user_id):
    with tracer.start_as_current_span("update_product") as span:
        data = request.json
        span.set_attribute("http.method", "PUT")
        span.set_attribute("http.route", "/products")
        span.set_attribute("user_id", current_user_id)
        logging.info("Product update request received", extra={"product_id": data.get("id"),"product_name": data.get("name") if data else "No data"})

        if not data or not data.get("id"):
            logging.warning("Product update failed - missing item ID")
            span.set_attribute("error", True)
            span.set_attribute("error.message", "mmissing product ID")
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

        span.set_attribute("update_name", new_product_name)
        span.set_attribute("update_price", new_price)
        span.set_attribute("update_quantity", new_quantity)
        span.set_attribute("update_description", new_description)

        if new_product_name:
            is_valid_name, name_result = ProductValidator.validate_product(new_product_name)
            if not is_valid_name:
                span.set_attribute("error", True)
                span.set_attribute("error.message", f"Invalid product name: {name_result}")
                logging.warning("Product name update failed - invalid product name", extra={"user_id": current_user_id, "product name": new_product_name})
                return jsonify({"error":f"Invalid product name: {name_result}"}), 400
            new_product_name = ProductValidator.sanitize_input(new_product_name).lower()
        
        if new_price:
            is_valid_price, price_result = ProductValidator.validate_product_price(new_price)
            if not is_valid_price:
                span.set_attribute("error", True)
                span.set_attribute("error.message", f"Invalid product price: {price_result}")
                logging.warning("Product price update failed - invalid price", extra={"user_id": current_user_id, "product price": new_price})
                return jsonify({"error":f"Invalid price: {price_result}"}), 400
        
        if new_quantity:
            is_valid_quantity, quantity_result = ProductValidator.validate_product_quantity(new_quantity)
            if not is_valid_quantity:
                span.set_attribute("error", True)
                span.set_attribute("error.message", f"Invalid product quantity: {quantity_result}")
                logging.warning("Product quantity update failed - invalid quantity", extra={"user_id": current_user_id, "product quantity": new_quantity})
                return jsonify({"error":f"Invalid quantity: {quantity_result}"}), 400
            
        if new_description:
            is_valid_description, description_result = ProductValidator.validate_product_description(new_description)
            if not is_valid_description:
                span.set_attribute("error", True)
                span.set_attribute("error.message", f"Invalid product description: {description_result}")
                logging.warning("Product description update failed - invalid description", extra={"user_id": current_user_id, "product description": new_description})
                return jsonify({"error":f"Invalid description: {description_result}"}), 400
            new_description = ProductValidator.sanitize_input(description_result)


        connection = get_db_connection()

        if not connection:
            logging.error("Database connection failed during producto update")
            span.set_attribute("error", True)
            span.set_attribute("error.message", "Database connection failed")
            span.set_status(Status(StatusCode.ERROR, "Database connection failed"))
            return jsonify({"Error": "Database connection failed"}), 500
    
    
        try:
            with connection.cursor() as cursor:
                with tracer.start_as_current_span("verify_product_query") as verify_span:
                    cursor.execute("SELECT id, name FROM items WHERE id = %s AND created_by = %s",(target_id,current_user_id))
                    selected_product = cursor.fetchone()
                    if not selected_product:
                        verify_span.set_attribute("product_exists", False)
                        return jsonify({"error":"product not found or access denied"}),404
                    verify_span.set_attribute("product.found", True)
                    if selected_product and "name" in selected_product:
                        verify_span.set_attribute("product.name", selected_product["name"])
                    else:
                        verify_span.set_attribute("product.name", "unknown")
                    
                with tracer.start_as_current_span("update_product_query") as update_span:    
                    if new_product_name is not None:# Allow empty name
                        cursor.execute("UPDATE items SET name = %s WHERE id = %s AND created_by = %s",(new_product_name, target_id, current_user_id))

                    if new_price is not None:# Allow zero price check above
                        cursor.execute("UPDATE items SET price = %s WHERE id = %s AND created_by = %s",(new_price, target_id, current_user_id))
                        
                    if new_description is not None:# Allow empty description
                        cursor.execute("UPDATE items SET description = %s WHERE id = %s AND created_by = %s",(new_description, target_id, current_user_id))

                    if new_quantity is not None:# Allow zero quantity
                        cursor.execute("UPDATE items SET quantity = %s WHERE id = %s AND created_by = %s",(new_quantity, target_id, current_user_id))
                    
                    connection.commit()
                    update_span.set_attribute("product.id", target_id)
                    update_span.set_attribute("rows_affected", cursor.rowcount)

                logging.info("Product updated succesfully", extra={"product_id":target_id})
                return jsonify({"message":"Product updated successfully"}), 200
        
        except Error as e:
            logging.error("Error updating product", extra={"error": str(e), "product_id": target_id})
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            span.set_status(Status(StatusCode.ERROR, str(e)))
            return jsonify({"error": "Failed to update product"}), 500
        
        finally:
            connection.close()


@app.route("/products", methods=["DELETE"])
@token_required
def delete_product(current_user_id):
    with tracer.start_as_current_span("delete_product") as span:
        data = request.get_json()
        span.set_attribute("http.method", "DELETE")
        span.set_attribute("http.route", "/products")
        span.set_attribute("user_id", current_user_id)
        logging.info("Product deletion request received", extra={"product_id": data.get("id") if data else "No data"})

        if not data or not data.get("id"):
            logging.warning("Product deletion failed - missing item ID")
            span.set_attribute("error", True)
            span.set_attribute("error.message", "missing item ID")
            return jsonify({"error": "Product ID of the item to be deleted required",
                            "example request":{"id":"1"}
                            })
    
        target_id = data["id"]
        connection = get_db_connection()

        if not connection:
            logging.error("Database connection failed during product deletion")
            span.set_attribute("error", True)
            span.set_attribute("error.message", "Database connection failed")
            span.set_status(Status(StatusCode.ERROR, "Database connection failed"))
            return jsonify({"error": "Database connection failed"}), 500
    
        try:
            with connection.cursor() as cursor: 
                with tracer.start_as_current_span("verify_product_query") as verify_span:
                    cursor.execute("SELECT * FROM items WHERE id = %s AND created_by =%s",(target_id, current_user_id))
                    product = cursor.fetchone()
                    if not product:
                        verify_span.set_attribute("product_exists", False)
                        logging.warning("Product deletion failed - product not found", extra={"product_id": target_id})
                        return jsonify({"error": "Product not found"}), 404
                    verify_span.set_attribute("product_found", True)
                    verify_span.set_attribute("product.name", product["name"])
                
                with tracer.start_as_current_span("delete_product_query") as delete_span:
                    cursor.execute("DELETE FROM items WHERE id = %s AND created_by = %s",(target_id, current_user_id))
                    connection.commit()
                    delete_span.set_attribute("product.id", target_id)
                    delete_span.set_attribute("rows_deleted", cursor.rowcount)            
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
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            span.set_status(Status(StatusCode.ERROR, str(e)))
            return jsonify({"error": "Failed to delete product"}),500
        
        finally:
            connection.close()


@app.route("/health", methods=["GET"])
def health_check():
    with tracer.start_as_current_span("health_check") as span:
        try:
            connection = get_db_connection()
            healthy = connection is not None
            if connection:
                connection.close()
            span.set_attribute("healthy", healthy)
            return jsonify({"status": "healthy" if healthy else "unhealthy"})
        except:
            span.set_attribute("healthy", False)
            span.set_attribute("error", True)
            span.set_status(Status(StatusCode.ERROR, "Health check failed"))
            return jsonify({"status": "unhealthy"}), 503
    

@app.route("/health/detailed",methods=["GET"])
def health_detailed():
    with tracer.start_as_current_span("detailed_health_check") as span:
        checks = {
            "database_connection": False,
            "database_query":False,
            "service_responsive":True
        }

        try:
            connection = get_db_connection()
            if connection:
                checks["database_connection"] = True
                span.set_attribute("database_connection", True)
                
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                    checks["database_query"] = True
                    span.set_attribute("database_query", True)
                connection.close()
    
        except Exception as e:
            logging.error(f"Health check error: {str(e)}")
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            span.set_status(Status(StatusCode.ERROR, f"Health check detailed failed: {str(e)}"))

        all_healthy = all(checks.values())
        status = "healthy" if all_healthy else "unhealthy"
        span.set_attribute("health.status", status)

        logging.info(f"Health check executed - Status: {status}", extra={"checks": checks})

        return jsonify({"status": status,
                        "service": "product-service", 
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "checks": checks
                            
                        }), 200 if all_healthy else 503


@app.route("/metrics",methods=["GET"])
def metrics():
        return jsonify({
            "service": "product-service",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_endpoints": ["/product", "/health","health/detailed", "/metrics"]
        })


def verify_db_setup():
    with tracer.start_as_current_span("verify_db_setup") as span:
        max_retries = 15
        retry_delay = 5  # seconds
        span.set_attribute("db_setup.max_retries", max_retries)

        for attempt in range(1, max_retries):
            with tracer.start_as_current_span(f"db_setup_attempt_{attempt}") as attempt_span:
                attempt_span.set_attribute("attempt_number", attempt)
                connection = None

                try: #Verify basic connectivity
                    connection = get_db_connection()
                    if not connection:
                        print(f"Database connection returned none, attempt: {attempt}")
                        attempt_span.set_attribute("db.connection_error", True)
                        attempt_span.set_status(Status(StatusCode.ERROR, "Database connection failed"))
                        raise Exception("Connection returned None")
                    
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        result = cursor.fetchone()
                        if not result:
                            raise Exception("Simple query SELECT 1 failed")
                        
                    print (f"Basic connectivity successful, attempt: {attempt}") # Posso remover esses prints?
                    attempt_span.set_attribute("db.connected", True)

                    with tracer.start_as_current_span("verify_items_table") as table_span: # Não preciso do try para ver se existe a tabela?
                        try:# Verify 'items' existence
                            with connection.cursor() as cursor:
                                cursor.execute("""
                                    SELECT COUNT(*) as table_exists
                                    FROM information_schema.tables
                                    WHERE table_schema = DATABASE()
                                    AND table_name = 'items'
                                    """)
                                result = cursor.fetchone()
                                exists = result['table_exists'] > 0 
                                table_span.set_attribute("items_table_exists", exists)

                                if exists:
                                    cursor.execute("SELECT COUNT(*) AS count FROM items")
                                    product_result = cursor.fetchone()
                                    product_count = product_result['count']
                                    table_span.set_attribute("db.items_count", product_count)
                                    print(f"tabel 'items' exists with {product_count} records")
                                else:
                                    print("table 'items' still not exists")
                                                                
                        except Exception as e:
                                table_span.set_attribute("error", True)
                                table_span.set_status(Status(StatusCode.ERROR, f"Table verification failed: {str(e)}"))
                                print(f"Table verification failed: {e}")              

                    span.set_attribute("db_setup.table_verification", True)
                    span.set_attribute("db_setup.attempts", attempt)
                    return True

                except Exception as e:
                    attempt_span.set_attribute("error", True)
                    attempt_span.set_status(Status(StatusCode.ERROR, f"Database setup verification failed: {str(e)}"))
                    print(f"Database setup verification attempt: {attempt} failed with error: {e}")

                    if attempt < max_retries:
                        print(f"attempt: {attempt} failed, retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        span.set_attribute("db_setup.max_retries_reached", True)
                        span.set_status(Status(StatusCode.ERROR, "Max retries reached for database setup verification"))
                        print("Max retries reached. Database setup verification failed")
                        return False
                    
                finally:
                    if connection:
                        try:
                            connection.close()
                        except Exception as close_err:
                            print(f"Failed to close connection: {close_err}")
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
    