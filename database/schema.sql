CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(50) DEFAULT 'manager'
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(100),
    current_price NUMERIC(10,2),
    cost_price NUMERIC(10,2),
    stock INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sales_records (
    id SERIAL PRIMARY KEY,
    product_name VARCHAR(150),
    units_sold INTEGER,
    revenue NUMERIC(12,2),
    price NUMERIC(10,2)
);

CREATE TABLE competitor_prices (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(50),
    competitor_name VARCHAR(100),
    competitor_product_name VARCHAR(150),
    competitor_url TEXT,
    competitor_price NUMERIC(10,2),
    currency VARCHAR(10) DEFAULT 'USD',
    availability VARCHAR(50) DEFAULT 'In Stock',
    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    previous_price NUMERIC(10,2),
    price_change NUMERIC(10,2),
    price_change_percent NUMERIC(10,2)
);

CREATE TABLE competitor_price_history (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(50),
    competitor_name VARCHAR(100),
    competitor_price NUMERIC(10,2),
    currency VARCHAR(10) DEFAULT 'USD',
    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE competitor_alerts (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(50),
    competitor_name VARCHAR(100),
    event_type VARCHAR(50),
    previous_price NUMERIC(10,2),
    current_price NUMERIC(10,2) NOT NULL,
    change_amount NUMERIC(10,2),
    change_percent NUMERIC(10,2),
    severity VARCHAR(20),
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_acknowledged BOOLEAN DEFAULT FALSE
);

INSERT INTO products (name, category, current_price, cost_price, stock) VALUES
('Wireless Headphones', 'Audio', 1999.00, 1299.00, 85),
('Smartwatch', 'Wearables', 3499.00, 2299.00, 64),
('Bluetooth Speaker', 'Audio', 1499.00, 899.00, 92),
('Gaming Mouse', 'Peripherals', 1199.00, 699.00, 120),
('Mechanical Keyboard', 'Peripherals', 2499.00, 1599.00, 78),
('4K Monitor', 'Displays', 18999.00, 12999.00, 47),
('Laptop', 'Computers', 59999.00, 44999.00, 36),
('Smartphone', 'Mobiles', 39999.00, 29999.00, 55),
('Tablet', 'Mobiles', 27999.00, 19999.00, 41),
('Webcam', 'Accessories', 3499.00, 2299.00, 70),
('External SSD', 'Storage', 8999.00, 5999.00, 63),
('Portable Charger', 'Accessories', 1999.00, 1199.00, 88),
('Smart Lamp', 'Home', 2999.00, 1899.00, 52),
('Fitness Band', 'Wearables', 2499.00, 1499.00, 74),
('Noise-Canceling Earbuds', 'Audio', 2999.00, 1799.00, 91);

INSERT INTO sales_records (product_name, units_sold, revenue, price) VALUES
('Wireless Headphones', 48, 95952.00, 1999.00),
('Smartwatch', 36, 125964.00, 3499.00),
('Bluetooth Speaker', 54, 80946.00, 1499.00),
('Gaming Mouse', 72, 86328.00, 1199.00),
('Mechanical Keyboard', 41, 102459.00, 2499.00),
('4K Monitor', 27, 512973.00, 18999.00),
('Laptop', 19, 1139981.00, 59999.00),
('Smartphone', 33, 1319967.00, 39999.00),
('Tablet', 22, 615978.00, 27999.00),
('Webcam', 60, 209940.00, 3499.00),
('External SSD', 28, 251972.00, 8999.00),
('Portable Charger', 67, 133933.00, 1999.00),
('Smart Lamp', 31, 92969.00, 2999.00),
('Fitness Band', 45, 112455.00, 2499.00),
('Noise-Canceling Earbuds', 58, 173942.00, 2999.00);
