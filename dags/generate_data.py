from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
import subprocess

def generate_logs():
    subprocess.run(["python", "/opt/airflow/scripts/generate_logs.py"], check=True)

def load_to_clickhouse():
    subprocess.run(["python", "/opt/airflow/scripts/load_to_clickhouse.py"], check=True)

def prepare_features():
    subprocess.run(["python", "/opt/airflow/scripts/prepare_features.py"], check=True)

def train_model():
    subprocess.run(["python", "/opt/airflow/scripts/train_model.py"], check=True)

with DAG(
    dag_id="generate_data",
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["data", "ml"],
) as dag:
    task_generate = PythonOperator(task_id="generate_logs", python_callable=generate_logs)
    task_load = PythonOperator(task_id="load_to_clickhouse", python_callable=load_to_clickhouse)
    task_prepare = PythonOperator(task_id="prepare_features", python_callable=prepare_features)
    task_train = PythonOperator(task_id="train_model", python_callable=train_model)

    task_generate >> task_load >> task_prepare >> task_train
