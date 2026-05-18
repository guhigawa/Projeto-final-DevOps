GRANT ALL PRIVILEGES ON auth.* TO 'auth_user'@'%';
FLUSH PRIVILEGES;

USE auth;

CREATE TABLE IF NOT EXISTS users(
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

INSERT IGNORE INTO users (email, password) VALUES ('guhigawa@gmail.com', 'admin123'); #Inserindo um user padrão para testes iniciais  