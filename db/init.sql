CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(150),
    city VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    name VARCHAR(150),
    category VARCHAR(100),
    price NUMERIC(12,2)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    order_date DATE
);

CREATE TABLE IF NOT EXISTS shipments (
    shipment_id INTEGER PRIMARY KEY,
    order_id INTEGER,
    status VARCHAR(50),
    shipped_date DATE
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id SERIAL PRIMARY KEY,
    pipeline VARCHAR(100),
    status VARCHAR(50),
    records INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP
);

CREATE OR REPLACE VIEW daily_revenue AS
SELECT
    o.order_date AS day,
    COALESCE(SUM(o.quantity * p.price), 0) AS revenue,
    COUNT(DISTINCT o.order_id) AS orders
FROM orders o
JOIN products p
    ON o.product_id = p.product_id
GROUP BY o.order_date
ORDER BY o.order_date;

CREATE OR REPLACE VIEW top_products AS
SELECT
    p.product_id,
    p.name AS product_name,
    COALESCE(SUM(o.quantity), 0) AS units,
    COALESCE(SUM(o.quantity * p.price), 0) AS revenue
FROM products p
LEFT JOIN orders o
    ON p.product_id = o.product_id
GROUP BY p.product_id, p.name
ORDER BY revenue DESC;