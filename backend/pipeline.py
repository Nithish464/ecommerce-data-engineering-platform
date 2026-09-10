import os
import pandas as pd
from sqlalchemy import create_engine, text

DB = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://pipeline:pipeline@localhost:5432/ecommerce",
)
BASE = os.path.join(os.path.dirname(__file__), "data")


def clean(df):
    df = df.drop_duplicates()
    for column in df.columns:
        if df[column].dtype == "object":
            df[column] = df[column].apply(
                lambda value: value.strip() if isinstance(value, str) else value
            )
    return df


def run():
    engine = create_engine(DB)
    files = ["customers", "products", "orders", "order_items", "shipments"]

    with engine.begin() as conn:
        run_id = conn.execute(text("""
            INSERT INTO pipeline_runs(pipeline, status, records)
            VALUES('batch_etl', 'running', 0)
            RETURNING run_id
        """)).scalar()

    total = 0

    try:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE order_items, shipments, orders, products, customers CASCADE"))
            conn.execute(text("TRUNCATE TABLE daily_revenue, top_products"))

        for name in files:
            path = os.path.join(BASE, f"{name}.csv")
            df = clean(pd.read_csv(path))

            if name in ("orders", "order_items", "shipments"):
                for column in df.columns:
                    if "date" in column or column.endswith("_at"):
                        df[column] = pd.to_datetime(df[column], errors="coerce")

            df.to_sql(name, engine, if_exists="append", index=False, method="multi")
            total += len(df)

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO daily_revenue(day, revenue, orders)
                SELECT order_date::date, SUM(total_amount), COUNT(*)
                FROM orders
                WHERE LOWER(status) <> 'cancelled'
                GROUP BY order_date::date
                ON CONFLICT(day) DO UPDATE SET
                    revenue=EXCLUDED.revenue,
                    orders=EXCLUDED.orders
            """))

            conn.execute(text("""
                INSERT INTO top_products(product_id, product_name, units, revenue)
                SELECT p.product_id,
                       p.name,
                       SUM(oi.quantity),
                       SUM(oi.quantity * oi.unit_price)
                FROM order_items oi
                JOIN orders o ON o.order_id=oi.order_id
                JOIN products p ON p.product_id=oi.product_id
                WHERE LOWER(o.status) <> 'cancelled'
                GROUP BY p.product_id, p.name
                ON CONFLICT(product_id) DO UPDATE SET
                    product_name=EXCLUDED.product_name,
                    units=EXCLUDED.units,
                    revenue=EXCLUDED.revenue
            """))

            conn.execute(text("""
                UPDATE pipeline_runs
                SET status='success', records=:records, finished_at=now()
                WHERE run_id=:run_id
            """), {"records": total, "run_id": run_id})

        print(f"[SUCCESS] Initial ETL completed. Records processed: {total}")

    except Exception:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE pipeline_runs
                SET status='failed', finished_at=now()
                WHERE run_id=:run_id
            """), {"run_id": run_id})
        raise


if __name__ == "__main__":
    run()
