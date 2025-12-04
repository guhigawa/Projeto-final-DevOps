USE user_staging;

INSERT IGNORE INTO users(email, password) VALUES
('staging-admin@example.com', 'staging_password_123'),
('staging-tester@example.com', 'staging_password_456');