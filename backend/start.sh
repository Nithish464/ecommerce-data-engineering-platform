#!/bin/sh
set -e

python - <<'PY'
import os
import time
from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
engine = create_engine(url)

for attempt in range(30):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[SUCCESS] PostgreSQL connection established")
        break
    except Exception:
        print(f"[INFO] Waiting for PostgreSQL... ({attempt + 1}/30)")
        time.sleep(2)
else:
    raise SystemExit("PostgreSQL did not become ready")

# Seed only once. The ETL truncates source tables, so it must never run on
# every API restart after users start creating/editing application data.
with engine.connect() as conn:
    successful_run = conn.execute(text("""
        SELECT COUNT(*)
        FROM pipeline_runs
        WHERE pipeline='batch_etl' AND status='success'
    """)).scalar() or 0

if successful_run == 0:
    print("[INFO] No successful initial ETL found. Running seed pipeline once...")
    from pipeline import run
    run()
else:
    print("[INFO] Initial ETL already completed. Preserving application data.")
PY

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
