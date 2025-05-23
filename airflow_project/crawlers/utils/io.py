import os
import pandas as pd
from dotenv import load_dotenv

# Đọc biến môi trường từ .env
load_dotenv()
BASE_DATA_DIR = os.getenv('DATA_DIR', 'data')


def save_raw_data(data: list, path: str = None) -> None:
    """
    Lưu `data` (list of dict) thành CSV.
    - Nếu `path` không truyền, lưu vào `{BASE_DATA_DIR}/raw/raw_data.csv`.
    - Nếu `path` là thư mục, lưu `raw_data.csv` vào thư mục đó.
    - Nếu `path` là file .csv, lưu trực tiếp.
    """
    df = pd.DataFrame(data)
    # Thiết lập mặc định
    if not path:
        raw_dir = os.path.join(BASE_DATA_DIR, 'raw')
        os.makedirs(raw_dir, exist_ok=True)
        path = os.path.join(raw_dir, 'raw_data.csv')
    # Nếu path là thư mục
    elif os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
        path = os.path.join(path, 'raw_data.csv')
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)

    df.to_csv(path, index=False)
    print(f"✅ Raw data saved to: {path}")


def save_processed_data(df: pd.DataFrame, path: str = None) -> None:
    """
    Lưu DataFrame đã xử lý:
    - Mặc định: `{BASE_DATA_DIR}/processed/processed_data.csv`.
    """
    if not path:
        proc_dir = os.path.join(BASE_DATA_DIR, 'processed')
        os.makedirs(proc_dir, exist_ok=True)
        path = os.path.join(proc_dir, 'processed_data.csv')
    elif os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
        path = os.path.join(path, 'processed_data.csv')
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)

    df.to_csv(path, index=False)
    print(f"✅ Processed data saved to: {path}")