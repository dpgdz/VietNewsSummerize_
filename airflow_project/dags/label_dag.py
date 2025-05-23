from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
import google.generativeai as genai

default_args = {
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
}

def label_articles():
    # Cấu hình API key của Gemini
    genai.configure(api_key="AIzaSyDbyeu_mamcJ_mnCz0x8rn9Bs01hb0ZGCc")

    # Load mô hình Gemini
    model = genai.GenerativeModel("models/gemini-2.0-flash")

    # Đường dẫn dữ liệu đã xử lý
    input_path = "/opt/airflow/data/processed/processed_data.csv"
    output_path = "/opt/airflow/data/processed/summarized_articles.csv"

    try:
        df = pd.read_csv(input_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Không tìm thấy file: {input_path}")

    def summarize_text(text):
        prompt = f"Tóm tắt văn bản sau trong 3 đến 4 câu:\n\n{text}"
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Lỗi: {e}"

    # Áp dụng Gemini để tóm tắt
    df["summary"] = df["content"].apply(summarize_text)

    # Ghi kết quả ra file
    df.to_csv(output_path, index=False)

with DAG(
    dag_id='label_articles_dag',  # Cần khớp với trigger_dag_id bên DAG crawl
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    description="DAG tóm tắt bài viết bằng Gemini",
    tags=["gemini", "label", "summary"]
) as dag:
    
    label_task = PythonOperator(
        task_id='label_articles',
        python_callable=label_articles,
    )

    label_task
