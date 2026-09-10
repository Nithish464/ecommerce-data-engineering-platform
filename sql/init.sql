CREATE TABLE IF NOT EXISTS customers (customer_id INT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, city TEXT, created_at DATE NOT NULL);
CREATE TABLE IF NOT EXISTS products (product_id INT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL, price NUMERIC(12,2) NOT NULL CHECK(price >= 0));
CREATE TABLE IF NOT EXISTS orders (order_id INT PRIMARY KEY, customer_id INT REFERENCES customers(customer_id), order_date TIMESTAMP NOT NULL, status TEXT NOT NULL, total_amount NUMERIC(12,2) NOT NULL CHECK(total_amount >= 0));
CREATE TABLE IF NOT EXISTS order_items (order_id INT REFERENCES orders(order_id), product_id INT REFERENCES products(product_id), quantity INT CHECK(quantity > 0), unit_price NUMERIC(12,2), PRIMARY KEY(order_id, product_id));
CREATE TABLE IF NOT EXISTS shipments (shipment_id SERIAL PRIMARY KEY, order_id INT REFERENCES orders(order_id), shipped_at TIMESTAMP, delivered_at TIMESTAMP, carrier TEXT);
CREATE TABLE IF NOT EXISTS daily_revenue (day DATE PRIMARY KEY, revenue NUMERIC(14,2), orders BIGINT);
CREATE TABLE IF NOT EXISTS top_products (product_id INT PRIMARY KEY, product_name TEXT, units BIGINT, revenue NUMERIC(14,2));
CREATE TABLE IF NOT EXISTS pipeline_runs (run_id SERIAL PRIMARY KEY, pipeline TEXT, status TEXT, records INT, started_at TIMESTAMP DEFAULT now(), finished_at TIMESTAMP);
