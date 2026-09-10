import os
from decimal import Decimal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://pipeline:pipeline@localhost:5432/ecommerce",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
app = FastAPI(title="E-Commerce Data Platform", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_STATUSES = {"processing", "shipped", "delivered", "cancelled"}


class CustomerPayload(BaseModel):
    name: str
    email: str
    city: str = ""


class ProductPayload(BaseModel):
    name: str
    category: str
    price: float


class OrderPayload(BaseModel):
    customer_id: int
    product_id: int
    quantity: int
    status: str = "processing"


def fetch_all(query, params=None):
    with engine.connect() as conn:
        return [dict(row._mapping) for row in conn.execute(text(query), params or {})]


def refresh_analytics(conn):
    conn.execute(text("DELETE FROM daily_revenue"))
    conn.execute(text("""
        INSERT INTO daily_revenue(day, revenue, orders)
        SELECT order_date::date,
               COALESCE(SUM(total_amount), 0),
               COUNT(*)
        FROM orders
        WHERE LOWER(status) <> 'cancelled'
        GROUP BY order_date::date
    """))

    conn.execute(text("DELETE FROM top_products"))
    conn.execute(text("""
        INSERT INTO top_products(product_id, product_name, units, revenue)
        SELECT p.product_id,
               p.name,
               COALESCE(SUM(oi.quantity), 0),
               COALESCE(SUM(oi.quantity * oi.unit_price), 0)
        FROM order_items oi
        JOIN orders o ON o.order_id = oi.order_id
        JOIN products p ON p.product_id = oi.product_id
        WHERE LOWER(o.status) <> 'cancelled'
        GROUP BY p.product_id, p.name
    """))


def next_id(conn, table, column, minimum=1):
    # Serialize ID generation so two simultaneous requests cannot choose the same ID.
    conn.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": hash(table) % 2147483647})
    return conn.execute(
        text(f"SELECT GREATEST(COALESCE(MAX({column}), :minimum - 1) + 1, :minimum) FROM {table}"),
        {"minimum": minimum},
    ).scalar()


@app.get("/")
def root():
    return {"message": "E-Commerce Data Platform API", "status": "running"}


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        return {"status": "error", "database": "disconnected", "error": str(exc)}


@app.get("/analytics/overview")
def analytics_overview():
    with engine.connect() as conn:
        orders = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar() or 0
        customers = conn.execute(text("SELECT COUNT(*) FROM customers")).scalar() or 0
        products = conn.execute(text("SELECT COUNT(*) FROM products")).scalar() or 0
        revenue = conn.execute(text("""
            SELECT COALESCE(SUM(total_amount), 0)
            FROM orders
            WHERE LOWER(status) <> 'cancelled'
        """)).scalar() or 0
        processing = conn.execute(text("SELECT COUNT(*) FROM orders WHERE LOWER(status)='processing'")).scalar() or 0
        shipped = conn.execute(text("SELECT COUNT(*) FROM orders WHERE LOWER(status)='shipped'")).scalar() or 0
        delivered = conn.execute(text("SELECT COUNT(*) FROM orders WHERE LOWER(status)='delivered'")).scalar() or 0
        cancelled = conn.execute(text("SELECT COUNT(*) FROM orders WHERE LOWER(status)='cancelled'")).scalar() or 0

    return {
        "orders": int(orders),
        "customers": int(customers),
        "products": int(products),
        "revenue": float(revenue),
        "processing": int(processing),
        "shipped": int(shipped),
        "delivered": int(delivered),
        "cancelled": int(cancelled),
    }


@app.get("/analytics/revenue")
def analytics_revenue():
    rows = fetch_all("SELECT day, revenue, orders FROM daily_revenue ORDER BY day")
    return [
        {"day": str(r["day"]), "revenue": float(r["revenue"] or 0), "orders": int(r["orders"] or 0)}
        for r in rows
    ]


@app.get("/analytics/top-products")
def analytics_top_products():
    rows = fetch_all("""
        SELECT product_id, product_name, units, revenue
        FROM top_products
        ORDER BY revenue DESC
        LIMIT 10
    """)
    return [
        {
            "product_id": int(r["product_id"]),
            "product_name": r["product_name"],
            "units": int(r["units"] or 0),
            "revenue": float(r["revenue"] or 0),
        }
        for r in rows
    ]


@app.get("/customers")
def get_customers():
    rows = fetch_all("""
        SELECT customer_id, name, email, city, created_at
        FROM customers
        ORDER BY customer_id DESC
    """)
    return [
        {
            "customer_id": int(r["customer_id"]),
            "name": r["name"],
            "email": r["email"],
            "city": r["city"] or "",
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]


@app.post("/customers")
def create_customer(payload: CustomerPayload):
    name, email, city = payload.name.strip(), payload.email.strip(), payload.city.strip()
    if not name or not email:
        raise HTTPException(400, "Name and email are required")
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(400, "Please enter a valid email")

    with engine.begin() as conn:
        if conn.execute(text("SELECT 1 FROM customers WHERE LOWER(email)=LOWER(:email)"), {"email": email}).scalar():
            raise HTTPException(400, "Email already exists")
        customer_id = next_id(conn, "customers", "customer_id")
        conn.execute(text("""
            INSERT INTO customers(customer_id, name, email, city, created_at)
            VALUES(:id, :name, :email, :city, CURRENT_DATE)
        """), {"id": customer_id, "name": name, "email": email, "city": city})
    return {"message": "Customer created successfully", "customer_id": int(customer_id)}


@app.put("/customers/{customer_id}")
def update_customer(customer_id: int, payload: CustomerPayload):
    name, email, city = payload.name.strip(), payload.email.strip(), payload.city.strip()
    if not name or not email:
        raise HTTPException(400, "Name and email are required")

    with engine.begin() as conn:
        if not conn.execute(text("SELECT 1 FROM customers WHERE customer_id=:id"), {"id": customer_id}).scalar():
            raise HTTPException(404, "Customer not found")
        if conn.execute(text("""
            SELECT 1 FROM customers
            WHERE LOWER(email)=LOWER(:email) AND customer_id<>:id
        """), {"email": email, "id": customer_id}).scalar():
            raise HTTPException(400, "Email already exists")
        conn.execute(text("""
            UPDATE customers
            SET name=:name, email=:email, city=:city
            WHERE customer_id=:id
        """), {"id": customer_id, "name": name, "email": email, "city": city})
    return {"message": "Customer updated successfully"}


@app.delete("/customers/{customer_id}")
def delete_customer(customer_id: int):
    with engine.begin() as conn:
        if not conn.execute(text("SELECT 1 FROM customers WHERE customer_id=:id"), {"id": customer_id}).scalar():
            raise HTTPException(404, "Customer not found")
        count = conn.execute(text("SELECT COUNT(*) FROM orders WHERE customer_id=:id"), {"id": customer_id}).scalar() or 0
        if count:
            raise HTTPException(400, "Customer has existing orders and cannot be deleted")
        conn.execute(text("DELETE FROM customers WHERE customer_id=:id"), {"id": customer_id})
    return {"message": "Customer deleted successfully"}


@app.get("/products")
def get_products():
    rows = fetch_all("""
        SELECT product_id, name, category, price
        FROM products
        ORDER BY product_id DESC
    """)
    return [
        {
            "product_id": int(r["product_id"]),
            "name": r["name"],
            "category": r["category"],
            "price": float(r["price"]),
        }
        for r in rows
    ]


@app.post("/products")
def create_product(payload: ProductPayload):
    name, category = payload.name.strip(), payload.category.strip()
    if not name or not category:
        raise HTTPException(400, "Product name and category are required")
    if payload.price < 0:
        raise HTTPException(400, "Price cannot be negative")

    with engine.begin() as conn:
        product_id = next_id(conn, "products", "product_id")
        conn.execute(text("""
            INSERT INTO products(product_id, name, category, price)
            VALUES(:id, :name, :category, :price)
        """), {"id": product_id, "name": name, "category": category, "price": payload.price})
    return {"message": "Product created successfully", "product_id": int(product_id)}


@app.put("/products/{product_id}")
def update_product(product_id: int, payload: ProductPayload):
    if payload.price < 0:
        raise HTTPException(400, "Price cannot be negative")

    with engine.begin() as conn:
        if not conn.execute(text("SELECT 1 FROM products WHERE product_id=:id"), {"id": product_id}).scalar():
            raise HTTPException(404, "Product not found")
        conn.execute(text("""
            UPDATE products
            SET name=:name, category=:category, price=:price
            WHERE product_id=:id
        """), {
            "id": product_id,
            "name": payload.name.strip(),
            "category": payload.category.strip(),
            "price": payload.price,
        })
    return {"message": "Product updated successfully"}


@app.delete("/products/{product_id}")
def delete_product(product_id: int):
    with engine.begin() as conn:
        if not conn.execute(text("SELECT 1 FROM products WHERE product_id=:id"), {"id": product_id}).scalar():
            raise HTTPException(404, "Product not found")
        count = conn.execute(text("SELECT COUNT(*) FROM order_items WHERE product_id=:id"), {"id": product_id}).scalar() or 0
        if count:
            raise HTTPException(400, "Product is used in existing orders and cannot be deleted")
        conn.execute(text("DELETE FROM products WHERE product_id=:id"), {"id": product_id})
    return {"message": "Product deleted successfully"}


@app.get("/orders")
def get_orders():
    # LATERAL returns at most one item per order, preventing duplicate order rows
    # when an old order contains multiple order_items.
    rows = fetch_all("""
        SELECT
            o.order_id,
            o.customer_id,
            c.name AS customer_name,
            o.order_date,
            o.status,
            o.total_amount,
            item.product_id,
            item.product_name,
            item.quantity,
            item.unit_price
        FROM orders o
        LEFT JOIN customers c ON c.customer_id=o.customer_id
        LEFT JOIN LATERAL (
            SELECT oi.product_id,
                   p.name AS product_name,
                   oi.quantity,
                   oi.unit_price
            FROM order_items oi
            LEFT JOIN products p ON p.product_id=oi.product_id
            WHERE oi.order_id=o.order_id
            ORDER BY oi.product_id
            LIMIT 1
        ) item ON TRUE
        ORDER BY o.order_date DESC, o.order_id DESC
    """)
    return [
        {
            "order_id": int(r["order_id"]),
            "customer_id": int(r["customer_id"]) if r["customer_id"] is not None else None,
            "customer_name": r["customer_name"] or "Unknown",
            "order_date": r["order_date"].isoformat() if r["order_date"] else None,
            "status": r["status"],
            "total_amount": float(r["total_amount"] or 0),
            "product_id": int(r["product_id"]) if r["product_id"] is not None else None,
            "product_name": r["product_name"] or "",
            "quantity": int(r["quantity"] or 0),
            "unit_price": float(r["unit_price"] or 0),
        }
        for r in rows
    ]


@app.post("/orders")
def create_order(payload: OrderPayload):
    if payload.quantity <= 0:
        raise HTTPException(400, "Quantity must be greater than 0")
    status = payload.status.strip().lower()
    if status not in VALID_STATUSES:
        raise HTTPException(400, "Invalid order status")

    with engine.begin() as conn:
        if not conn.execute(text("SELECT 1 FROM customers WHERE customer_id=:id"), {"id": payload.customer_id}).scalar():
            raise HTTPException(404, "Customer not found")

        product = conn.execute(text("SELECT price FROM products WHERE product_id=:id"), {"id": payload.product_id}).mappings().first()
        if not product:
            raise HTTPException(404, "Product not found")

        price = Decimal(str(product["price"]))
        total = price * payload.quantity
        order_id = next_id(conn, "orders", "order_id", minimum=1001)

        conn.execute(text("""
            INSERT INTO orders(order_id, customer_id, order_date, status, total_amount)
            VALUES(:id, :customer_id, NOW(), :status, :total)
        """), {
            "id": order_id,
            "customer_id": payload.customer_id,
            "status": status,
            "total": total,
        })

        conn.execute(text("""
            INSERT INTO order_items(order_id, product_id, quantity, unit_price)
            VALUES(:order_id, :product_id, :quantity, :price)
        """), {
            "order_id": order_id,
            "product_id": payload.product_id,
            "quantity": payload.quantity,
            "price": price,
        })

        refresh_analytics(conn)

    return {
        "message": "Order created successfully",
        "order_id": int(order_id),
        "total_amount": float(total),
    }


@app.put("/orders/{order_id}")
def update_order(order_id: int, payload: OrderPayload):
    if payload.quantity <= 0:
        raise HTTPException(400, "Quantity must be greater than 0")
    status = payload.status.strip().lower()
    if status not in VALID_STATUSES:
        raise HTTPException(400, "Invalid order status")

    with engine.begin() as conn:
        if not conn.execute(text("SELECT 1 FROM orders WHERE order_id=:id"), {"id": order_id}).scalar():
            raise HTTPException(404, "Order not found")
        if not conn.execute(text("SELECT 1 FROM customers WHERE customer_id=:id"), {"id": payload.customer_id}).scalar():
            raise HTTPException(404, "Customer not found")

        product = conn.execute(text("SELECT price FROM products WHERE product_id=:id"), {"id": payload.product_id}).mappings().first()
        if not product:
            raise HTTPException(404, "Product not found")

        price = Decimal(str(product["price"]))
        total = price * payload.quantity

        conn.execute(text("""
            UPDATE orders
            SET customer_id=:customer_id, status=:status, total_amount=:total
            WHERE order_id=:id
        """), {
            "id": order_id,
            "customer_id": payload.customer_id,
            "status": status,
            "total": total,
        })

        conn.execute(text("DELETE FROM order_items WHERE order_id=:id"), {"id": order_id})
        conn.execute(text("""
            INSERT INTO order_items(order_id, product_id, quantity, unit_price)
            VALUES(:order_id, :product_id, :quantity, :price)
        """), {
            "order_id": order_id,
            "product_id": payload.product_id,
            "quantity": payload.quantity,
            "price": price,
        })

        refresh_analytics(conn)

    return {"message": "Order updated successfully", "total_amount": float(total)}


@app.delete("/orders/{order_id}")
def delete_order(order_id: int):
    with engine.begin() as conn:
        if not conn.execute(text("SELECT 1 FROM orders WHERE order_id=:id"), {"id": order_id}).scalar():
            raise HTTPException(404, "Order not found")

        conn.execute(text("DELETE FROM order_items WHERE order_id=:id"), {"id": order_id})
        conn.execute(text("DELETE FROM shipments WHERE order_id=:id"), {"id": order_id})
        conn.execute(text("DELETE FROM orders WHERE order_id=:id"), {"id": order_id})
        refresh_analytics(conn)

    return {"message": "Order deleted successfully"}


@app.get("/pipeline/runs")
def pipeline_runs():
    rows = fetch_all("""
        SELECT run_id, pipeline, status, records, started_at, finished_at
        FROM pipeline_runs
        ORDER BY run_id DESC
        LIMIT 20
    """)
    return [
        {
            "run_id": int(r["run_id"]),
            "pipeline": r["pipeline"],
            "status": r["status"],
            "records": int(r["records"] or 0),
            "started_at": r["started_at"].isoformat() if r["started_at"] else None,
            "finished_at": r["finished_at"].isoformat() if r["finished_at"] else None,
        }
        for r in rows
    ]


@app.get("/pipeline/health")
def pipeline_health():
    rows = fetch_all("""
        SELECT pipeline, status, records, started_at, finished_at
        FROM pipeline_runs
        ORDER BY run_id DESC
        LIMIT 1
    """)
    if not rows:
        return {"status": "unknown", "pipeline": None, "records": 0}
    r = rows[0]
    return {
        "status": r["status"],
        "pipeline": r["pipeline"],
        "records": int(r["records"] or 0),
        "started_at": r["started_at"].isoformat() if r["started_at"] else None,
        "finished_at": r["finished_at"].isoformat() if r["finished_at"] else None,
    }
