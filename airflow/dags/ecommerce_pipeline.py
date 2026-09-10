from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
sys.path.append('/opt/airflow/etl')
from pipeline import run
with DAG('ecommerce_batch_pipeline',start_date=datetime(2026,1,1),schedule='@daily',catchup=False,default_args={'retries':2,'retry_delay':timedelta(minutes=2)}) as dag:
    PythonOperator(task_id='run_etl_and_analytics',python_callable=run)
