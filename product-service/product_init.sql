CREATE USER IF NOT EXISTS 'product_user'@'localhost' IDENTIFIED BY 'prodpass123';

CREATE database IF NOT EXISTS products;

GRANT ALL PRIVILEGES ON products.* TO 'product_user'@'localhost';

USE products;

CREATE TABLE items(
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