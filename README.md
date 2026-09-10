# E-Commerce Data Engineering Pipeline

End-to-end data engineering demo with Python, PostgreSQL, Airflow, Kafka, PySpark, FastAPI, React and Docker.

## Run

```bash
docker compose up --build
```

- Dashboard: http://localhost:3000
- API: http://localhost:8000/docs
- Airflow: http://localhost:8080 (admin/admin)
- Kafka: localhost:9092
- PostgreSQL: localhost:5432

The dashboard uses live API data generated from PostgreSQL. The project includes batch ETL, Kafka order events, Spark transformations, Airflow orchestration and data-quality checks.

## Architecture

CSV/API -> Python ETL -> PostgreSQL staging -> Spark transformations -> analytics tables
                    |                         ^
                    v                         |
                  Kafka -> consumer ----------+
                    |
                  FastAPI -> React dashboard

Airflow orchestrates the batch pipeline.
