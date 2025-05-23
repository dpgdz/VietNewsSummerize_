from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from datetime import datetime
import sys
import os

# Thêm đường dẫn gốc để import được main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import main  # <-- Gọi trực tiếp hàm main

with DAG(
    dag_id="run_main_crawler_dag",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    tags=["crawler", "main"]
) as dag:

    run_main_task = PythonOperator(
        task_id="run_main_crawler",
        python_callable=main
    )

    trigger_label_dag = TriggerDagRunOperator(
        task_id="trigger_label_dag",
        trigger_dag_id="label_articles_dag",  # Tên chính xác của DAG tóm tắt
        wait_for_completion=True  # Chờ DAG tóm tắt hoàn thành (nếu cần)
    )

    run_main_task >> trigger_label_dag
