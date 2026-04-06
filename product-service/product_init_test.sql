CREATE USER IF NOT EXISTS 'product_test_user'@'%' IDENTIFIED BY 'test_password_123';
CREATE USER IF NOT EXISTS 'product_test_user'@'localhost' IDENTIFIED BY 'test_password_123';

CREATE DATABASE IF NOT EXISTS products_test;

GRANT SELECT, INSERT, UPDATE, DELETE ON products_test.*  TO 'product_test_user'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON products_test.*  TO 'product_test_user'@'localhost';

FLUSH PRIVILEGES;

USE products_test;

CREATE TABLE IF NOT EXISTS items(
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    quantity int NOT NULL DEFAULT 0,
    price DECIMAL(10, 2) NOT NULL,
    description TEXT NULL,
    created_by int NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_created_by (created_by),
    INDEX idx_created_at (created_at),
    INDEX idx_name (name)
);


INSERT IGNORE INTO items (name, quantity, price, description, created_by) VALUES 
('Test Product 1', 10, 29.99, 'Description for test product 1', 1),
('Test Product 2', 5, 49.99, 'Description for test product 2', 1);