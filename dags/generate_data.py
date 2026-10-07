from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
import subprocess

def generate_logs():
    subprocess.run(["python", "/opt/airflow/scripts/generate_logs.py"], check=True)

def load_to_clickhouse():
    subprocess.run(["python", "/opt/airflow/scripts/load_to_clickhouse.py"], check=True)

with DAG(
    dag_id="generate_data",
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["data"],
) as dag:
    task_generate = PythonOperator(
        task_id="generate_logs",
        python_callable=generate_logs,
    )
    task_load = PythonOperator(
        task_id="load_to_clickhouse",
        python_callable=load_to_clickhouse,
    )
    task_generate >> task_load
