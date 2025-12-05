USE product_staging;

INSERT IGNORE INTO items (name, quantity, price, description) VALUES
('Item A', 100, 19.99, 'Description for Item A'),
('Item B', 50, 29.99, 'Description for Item B'),
('Item C', 200, 9.99, 'Description for Item C'),
('Item D', 150, 14.99, 'Description for Item D'),
('Item E', 75, 24.99, 'Description for Item E');