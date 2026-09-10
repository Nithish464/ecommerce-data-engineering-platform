#!/bin/sh
set -e

python - <<'PY'
import os
import time
from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
engine = create_engine(url)

# ---------------------------------------------------------
# Wait for PostgreSQL
# ---------------------------------------------------------
for attempt in range(30):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[SUCCESS] PostgreSQL connection established")
        break
    except Exception as exc:
        print(f"[INFO] Waiting for PostgreSQL... ({attempt + 1}/30)")
        time.sleep(2)
else:
    raise SystemExit("PostgreSQL did not become ready")

# ---------------------------------------------------------
# Check whether the initial ETL has already been recorded
# ---------------------------------------------------------
with engine.connect() as conn:
    successful_run = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM pipeline_runs
            WHERE pipeline = 'batch_etl'
              AND status = 'success'
        """)
    ).scalar() or 0

    customer_count = conn.execute(
        text("SELECT COUNT(*) FROM customers")
    ).scalar() or 0

    product_count = conn.execute(
        text("SELECT COUNT(*) FROM products")
    ).scalar() or 0

    order_count = conn.execute(
        text("SELECT COUNT(*) FROM orders")
    ).scalar() or 0

    order_item_count = conn.execute(
        text("SELECT COUNT(*) FROM order_items")
    ).scalar() or 0

    shipment_count = conn.execute(
        text("SELECT COUNT(*) FROM shipments")
    ).scalar() or 0

# ---------------------------------------------------------
# Run ETL only when database is empty.
#
# IMPORTANT:
# The ETL truncates source/application tables.
# Therefore, never run it automatically when real application
# data already exists.
# ---------------------------------------------------------
if successful_run == 0:

    if (
        customer_count == 0
        and product_count == 0
        and order_count == 0
        and order_item_count == 0
        and shipment_count == 0
    ):
        print("[INFO] Database is empty. Running initial ETL...")

        from pipeline import run

        run()

    else:
        # Existing application data is already present.
        # Do not destroy it with the destructive seed ETL.
        # Instead, create a successful pipeline history record
        # representing the currently loaded dataset.
        records = (
            customer_count
            + product_count
            + order_count
            + order_item_count
            + shipment_count
        )

        print(
            "[INFO] Existing application data detected. "
            "Skipping destructive initial ETL."
        )

        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO pipeline_runs(
                        pipeline,
                        status,
                        records,
                        started_at,
                        finished_at
                    )
                    VALUES(
                        'batch_etl',
                        'success',
                        :records,
                        now(),
                        now()
                    )
                """),
                {"records": records},
            )

        print(
            f"[SUCCESS] Pipeline history initialized. "
            f"Existing records: {records}"
        )

else:
    print(
        "[INFO] Initial ETL/pipeline history already exists. "
        "Preserving application data."
    )

PY

# ---------------------------------------------------------
# Start FastAPI
# ---------------------------------------------------------
exec uvicorn app.main:app --host 0.0.0.0 --port 8000