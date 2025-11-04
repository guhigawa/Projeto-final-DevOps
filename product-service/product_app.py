import jwt,datetime,os,pymysql,logging, time;
from functools import wraps
from flask import Flask, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from pymysql import Error

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'product_fallback_secret')


app.config["MYSQL_HOST"] = os.environ.get("MYSQL_HOST", "localhost")
app.config["MYSQL_USER"] = os.environ.get("MYSQL_USER","product_user")
app.config["MYSQL_PASSWORD"] = os.environ.get("MYSQL_PASSWORD","prodpass123")
app.config["MYSQL_DB"] = os.environ.get("MYSQL_DB","products")
app.config["MYSQL_PORT"] = os.environ.get("MYSQL_PORT","3306")

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
            db=app.config["MYSQL_DB"],
            port=int(app.config["MYSQL_PORT"]),
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Error as e:
        logging.error(f"Error connecting to prducts database: {e}")
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
    logging.info("product creation request received", extra={"name" : data.get("name"),"price":data.get("price") if data else "No data"})
    
    if not data or not data.get("name") or not data.get("price"):
        logging.warning("Product creation failed - missing fields")
        return jsonify({"error": "Name and price are required",
                        "example_request":{"name":"Test Product",
                                           "price": "9.99",
                                           "description": "optional description",
                                           "quantity":"1 (if not provided, defaults to 0)"}
                        }), 400
    
    try:
        name = str(data["name"])
        price = float(data["price"])
        if price <= 0:
            return jsonify({"error": "Price must bigger than 0"}), 400
        quantity = int(data.get("quantity", 0))
        if quantity < 0:
            return jsonify({"error": "Quantity cannot be negative"}), 400
    except (ValueError, TypeError) as e:
        logging.warning("Product creation failed - invalid data types")
        return jsonify({"error": f"Invalid data format: {str(e)}"}), 400

    connection = get_db_connection()
    if not connection:
        logging.error("Database connection failed during product creation")
        return jsonify({"error": "Database connection failed"}), 500    

    try:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO items (name, price,quantity, description, created_by) VALUES (%s, %s, %s, %s, %s)",
                           (name, price, data.get("description"), current_user_id))
            
            product_id = cursor.lastrowid
            connection.commit()
            logging.info(f"Product created", extra ={"product_id": product_id, "name": name})
            return jsonify({"message": "Product created successfully", 
                            "product_id": product_id,
                            "product_name":name}), 201
        
    except Error as e:
        logging.error("Product creation error:", extra={"error": str(e)})
        return jsonify({"error": "Failed to create product"}), 500
    
    finally:
        connection.close()
    

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3002, debug=True)
    