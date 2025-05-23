import pandas as pd
import re
import os
import unicodedata
from bs4 import BeautifulSoup


def clean_text(text):
    if pd.isnull(text):
        return text
    # Remove HTML tags
    text = BeautifulSoup(text, "html.parser").get_text()
    # Normalize unicode
    text = unicodedata.normalize("NFKC", text)
    # Remove redundant whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def preprocess_news(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"[!] File {input_path} không tồn tại.")
        return

    df = pd.read_csv(input_path)

    # Drop duplicates by 'link'
    df = df.drop_duplicates(subset='link')

    # Fill NaN author with 'Unknown'
    df['author'] = df['author'].fillna('Unknown')

    # Drop rows where 'content' or 'date' is NaN
    df = df.dropna(subset=['content', 'date'])

    # Clean text columns
    for col in ['title', 'content', 'author']:
        df[col] = df[col].apply(clean_text)

    # Save cleaned file
    df.to_csv(output_path, index=False)
    print(f"[+] Đã lưu dữ liệu đã xử lý vào: {output_path}")


if __name__ == "__main__":
    preprocess_news("data/Data/vnexpress_articles.csv", "data/Data/vnexpress_process.csv")