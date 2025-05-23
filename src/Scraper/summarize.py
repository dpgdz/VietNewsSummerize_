
    
import pandas as pd
import google.generativeai as genai
import os
import time
from tqdm import tqdm
from datetime import datetime

# Danh sách API keys dự phòng
API_KEYS = [
    "AIzaSyDbyeu_mamcJ_mnCz0x8rn9Bs01hb0ZGCc",
    "AIzaSyDBXNxq_PbOoSPqv-5GJCwvWH0oq1osQmk",
    "AIzaSyDQswTsiCWLMTnSXseMQVZakafp22t7DVM",
    "AIzaSyCqslFtxh5PDhzdmsxfZy7ZYRl-q2Z0v_w",
    "AIzaSyAxyvaRN6fu4nehGap3xfDCaLUHdM0_YG0",
    "AIzaSyCFUllRgNCmXweTClrsGxQY6vWY0HN4_Jw",
    "AIzaSyA4LvQA-8waUaDXK0blWtO-WK4h8SmJ_70",
    "AIzaSyAIk45prXMSj8CUCEvWgdGNaJ4pMoSJvPk",
    "AIzaSyDEw9gZtUqms58TxWTfEgBPWQhdOEte5pQ",
    "AIzaSyD_BpKqaSl0pgknBvdef0aLIRsxkMAOMBo",
    "AIzaSyDv-vLnvpAU9jC7Bl1OmNZFzCUhlZT5UH4",
    "AIzaSyCREujHFsB7g4zLt6f-nwbAIYyO7pogcJw",
    "AIzaSyCU1_x3mIdILIAaLm1zAc51AOv7RrGROig"
]

# Thiết lập API key đầu tiên
current_key_index = 0
genai.configure(api_key=API_KEYS[current_key_index])
model = genai.GenerativeModel("models/gemini-2.0-flash")

def switch_api_key():
    global current_key_index, model
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    genai.configure(api_key=API_KEYS[current_key_index])
    model = genai.GenerativeModel("models/gemini-2.0-flash")
    print(f"[!] Đã chuyển sang API key thứ {current_key_index + 1}/{len(API_KEYS)}")

# Hàm tóm tắt văn bản
def summarize_text(text, max_len=3000, retry=3):
    text = str(text)
    if len(text) > max_len:
        text = text[:max_len]

    prompt = f"Tóm tắt văn bản sau trong 3 đến 4 câu:\n\n{text}"

    for _ in range(retry):
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"[!] Lỗi khi gọi API: {e}")
            switch_api_key()
            time.sleep(1)
    return ""

# Hàm tóm tắt file tin tức
def summarize_news(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"[!] File {input_path} không tồn tại.")
        return

    df = pd.read_csv(input_path)

    if "content" not in df.columns or "id" not in df.columns:
        print(f"[!] Thiếu cột 'content' hoặc 'id' trong file {input_path}.")
        return

    # Lấy ngày hôm nay theo định dạng ddmmyy
    today_str = datetime.today().strftime("%d%m%y")

    # Lọc các bài có id chứa ngày hôm nay
    df_today = df[df["id"].astype(str).str.contains(today_str)]
    print(f"[*] Có {len(df_today)} bài viết của ngày hôm nay ({today_str}).")

    if df_today.empty:
        print("[*] Không có bài viết nào hôm nay.")
        return

    # Lấy ngẫu nhiên 50 bài (hoặc ít hơn nếu không đủ)
    df_to_summarize = df_today.sample(n=min(50, len(df_today)), random_state=42)

    tqdm.pandas()
    df_to_summarize["summary"] = df_to_summarize["content"].progress_apply(summarize_text)

    df_to_summarize.to_csv(output_path, index=False)
    print(f"[+] Đã lưu kết quả tóm tắt vào: {output_path}")

# Chạy nhiều file
if __name__ == "__main__":
    file_pairs = [
        (
            "data/Data/data_raw_cleaned.csv",
            "data/Data/data_process_summarized.csv"
        )
    ]

    for input_file, output_file in file_pairs:
        print(f"\n=== TÓM TẮT FILE: {input_file} ===")
        summarize_news(input_file, output_file)
