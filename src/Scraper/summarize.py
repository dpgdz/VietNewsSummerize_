import pandas as pd
import google.generativeai as genai
import os
import time

# ===== 1. Danh sách API keys =====
API_KEYS = {
    "key1": "AIzaSyDbyeu_mamcJ_mnCz0x8rn9Bs01hb0ZGCc",
    "key2": "AIzaSyDBXNxq_PbOoSPqv-5GJCwvWH0oq1osQmk",
    "key3": "AIzaSyDQswTsiCWLMTnSXseMQVZakafp22t7DVM",
    "key4": "AIzaSyCqslFtxh5PDhzdmsxfZy7ZYRl-q2Z0v_w",
    "key5": "AIzaSyAxyvaRN6fu4nehGap3xfDCaLUHdM0_YG0",
    "key6": "AIzaSyCFUllRgNCmXweTClrsGxQY6vWY0HN4_Jw",
    "key7": "AIzaSyDYK4LxQo9-silCZIfQ7dqZZecdhTA_el4",
    "key8": "AIzaSyA4LvQA-8waUaDXK0blWtO-WK4h8SmJ_70",
    "key9": "AIzaSyBCauksOW9ldpzh33E4ZpjyLdl9m3MSS7c",
    "key10": "AIzaSyAIk45prXMSj8CUCEvWgdGNaJ4pMoSJvPk",
    "key11": "AIzaSyDEw9gZtUqms58TxWTfEgBPWQhdOEte5pQ",
    "key12": "AIzaSyCB2anT6gyrEPkccDo-MuvXPrGw3xQPwQc",
    "key13": "AIzaSyDv-vLnvpAU9jC7Bl1OmNZFzCUhlZT5UH4",
    "key14": "AIzaSyD_BpKqaSl0pgknBvdef0aLIRsxkMAOMBo",
    "key15": "AIzaSyAMm6SraniUoWBFaIrkeFc19G7zK39F--E",
    "key16": "AIzaSyBmkbV2FTCiHiUtI74AZ7cJoCBtwPgeiew",
}

# ===== 2. Hàm tạo model từ API key =====
def load_model(api_key):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("models/gemini-2.0-flash")

# ===== 3. Hàm tóm tắt 1 đoạn văn bản =====
def summarize_text(text, max_len=3000):
    text = str(text)
    if len(text) > max_len:
        text = text[:max_len]

    prompt = f"Tóm tắt văn bản sau trong 3 đến 4 câu:\n\n{text}"

    max_attempts = 3
    for attempt in range(max_attempts):
        for name, key in API_KEYS.items():
            try:
                model = load_model(key)
                response = model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    print(f"[!] Key '{name}' bị quota (429). Thử key khác...")
                else:
                    print(f"[!] Lỗi với key '{name}': {e}")
                continue
        # Nếu tất cả key đều fail
        print(f"[!] Tạm nghỉ 15 giây (lần {attempt+1}/{max_attempts}) vì quota toàn bộ...")
        time.sleep(15)

    return "[!] Tóm tắt thất bại vì quá hạn mức."

# ===== 4. Hàm xử lý tóm tắt toàn bộ file =====
def summarize_news(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"[!] File {input_path} không tồn tại.")
        return

    df = pd.read_csv(input_path)

    if "content" not in df.columns:
        print(f"[!] Không tìm thấy cột 'content' trong file {input_path}.")
        return

    print(f"[*] Bắt đầu tóm tắt: {len(df)} dòng từ {input_path}")
    
    summaries = []
    for idx, content in enumerate(df["content"]):
        print(f"[{idx+1}/{len(df)}] Đang tóm tắt...")
        summary = summarize_text(content)
        summaries.append(summary)

    df["summary"] = summaries
    df.to_csv(output_path, index=False)
    print(f"[+] Đã lưu dữ liệu tóm tắt vào: {output_path}")

# ===== 5. Run trực tiếp =====
if __name__ == "__main__":
    summarize_news(
        "data/Data/vnexpress_process.csv",
        "data/Data/vnexpress_summarized.csv"
    )