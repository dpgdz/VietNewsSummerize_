import json
import os
from scraper_factory import get_scraper
from preprocessing import preprocess_news
from summarize import summarize_news  

current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, "src", "config", "config_data.json")

with open(config_path, "r") as f:
    config = json.load(f)

def run_scraper(cfg):
    scraper = get_scraper(
        cfg["name"], cfg["headle"], cfg["base_url"],
        cfg["output_csv"], cfg["process"]
    )
    scraper.scrape()
    # Kiểm tra file có được tạo sau scrape không
    if os.path.exists(cfg["output_csv"]):
        print(f"[+] File {cfg['output_csv']} đã được tạo.")
    else:
        print(f"[!] File {cfg['output_csv']} chưa được tạo, kiểm tra lại bước scrape.")
        return  # Nếu chưa có file thì dừng luôn

    # Preprocess dữ liệu
    preprocess_news(cfg["output_csv"], cfg["process"])

    # Summarize
    summarize_news(cfg["process"], cfg["output_csv"].replace(".csv", "_summarized.csv"))

if __name__ == '__main__':
    for cfg in config:
        run_scraper(cfg)
        