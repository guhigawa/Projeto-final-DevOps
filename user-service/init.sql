CREATE USER 'auth_user'@'localhost' IDENTIFIED BY 'password123'; #Criando o user para acesso ao MySQL database

CREATE database auth;

GRANT ALL PRIVILEGES ON auth.* TO 'auth_user'@'localhost'; #Dando permissão ao user criado para acessar o database auth

USE auth;

CREATE TABLE users(
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

INSERT INTO users (email, password) VALUES ('guhigawa@gmail.com', 'admin123'); #Inserindo um user padrão para testes iniciais  