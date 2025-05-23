from base_scraper import BaseScraper
import requests
from bs4 import BeautifulSoup
import time
import os
import pandas as pd
from datetime import datetime
import random

class DanTriScraper(BaseScraper):
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1',
        # Thêm user-agent nếu muốn
    ]

    def __init__(self, headle, base_url, output_csv, original_csv):
        super().__init__(headle, base_url, output_csv, original_csv)

    def get_random_headers(self):
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Referer': 'https://dantri.com.vn/'
        }

    def get_with_retry(self, url, retries=4, delay=5):
        for i in range(retries):
            try:
                headers = self.get_random_headers()
                res = requests.get(url, headers=headers, timeout=10)
                res.encoding = 'utf-8'

                if res.status_code == 429:
                    print(f"[!] Bị chặn 429 tại {url}, đợi {delay} giây rồi thử lại ({i+1}/{retries})")
                    time.sleep(delay)
                    delay *= 2
                    continue
                elif res.status_code >= 500:
                    print(f"[!] Lỗi server {res.status_code} tại {url}, đợi {delay} giây rồi thử lại ({i+1}/{retries})")
                    time.sleep(delay)
                    delay *= 2
                    continue

                return res
            except requests.RequestException as e:
                print(f"[!] Lỗi kết nối {url}: {e}, đợi {delay} giây rồi thử lại ({i+1}/{retries})")
                time.sleep(delay)
                delay *= 2
        print(f"[!] Không thể lấy được trang {url} sau {retries} lần thử.")
        return None

    def get_categories(self):
        url = 'https://dantri.com.vn/'
        res = self.get_with_retry(url)
        if res is None:
            return []

        soup = BeautifulSoup(res.text, 'html.parser')
        menu = soup.find('ol', class_='menu-wrap')

        categories = []

        if not menu:
            print("[!] Không tìm thấy menu chính, trả về danh sách rỗng.")
            return categories

        for li in menu.find_all('li', recursive=False):
            a_tag = li.find('a')
            if not a_tag or a_tag.get('href') == 'https://dantri.com.vn/':
                continue  # Bỏ qua "Trang chủ"

            category_name = a_tag.get_text(strip=True)
            category_link = a_tag['href']
            if not category_link.startswith("http"):
                category_link = "https://dantri.com.vn" + category_link

            submenu = li.find('ol', class_='submenu')
            if submenu:
                for sub_li in submenu.find_all('li'):
                    sub_a = sub_li.find('a')
                    if sub_a:
                        sub_name = sub_a.get_text(strip=True)
                        sub_link = sub_a['href']
                        if not sub_link.startswith("http"):
                            sub_link = "https://dantri.com.vn" + sub_link
                        categories.append((category_name, sub_name, sub_link))
            else:
                categories.append((category_name, "", category_link))

        print(f"[DEBUG] Lấy được {len(categories)} chuyên mục.")
        return categories

    def get_article_details(self, link):
        res = self.get_with_retry(link)
        if res is None or res.status_code != 200:
            print(f"[!] Không lấy được bài: {link} - status_code: {res.status_code if res else 'No Response'}")
            return "", "", "", "", ""

        try:
            soup = BeautifulSoup(res.text, 'html.parser')

            content_div = soup.find("div", class_="singular-content")
            content = content_div.get_text(separator="\n", strip=True) if content_div else ""

            breadcrumbs = soup.find("ul", class_="breadcrumb")
            category = sub_category = ""
            if breadcrumbs:
                items = breadcrumbs.find_all("li")
                if len(items) >= 2:
                    category = items[1].get_text(strip=True)
                if len(items) >= 3:
                    sub_category = items[2].get_text(strip=True)

            author = ""
            author_div = soup.find("div", class_="author-name")
            if author_div:
                author_name_tag = author_div.find("b")
                if author_name_tag:
                    author = author_name_tag.get_text(strip=True)

            date_str = ""
            time_tag = soup.find("time", class_="author-time")
            if time_tag:
                if time_tag.has_attr("datetime"):
                    date_str = time_tag["datetime"].strip()
                else:
                    date_str = time_tag.get_text(strip=True)


            if not content or not date_str:
                print(f"[!] Cảnh báo: Bài {link} thiếu nội dung hoặc ngày đăng")

            return content, author, category, sub_category, date_str
        except Exception as e:
            print(f"[!] Lỗi khi lấy chi tiết bài {link}: {e}")
            return "", "", "", "", ""

    def is_today(self, date_str):
        try:
            date_part = date_str.split(' ')[0]  # lấy phần ngày yyyy-mm-dd
            date_obj = datetime.strptime(date_part, "%Y-%m-%d")
            return date_obj.date() == datetime.now().date()
        except:
            return False

    def scrape(self):
        print("[+] Bắt đầu crawl Dân Trí...")
        categories = self.get_categories()
        article_counter = 1
        today_str = datetime.now().strftime("%d%m%y")

        for main_cat, sub_cat, base_url in categories:
            for page in range(1, 3):  # chỉ lấy trang 1 để đảm bảo bài hôm nay
                url = base_url if page == 1 else f"{base_url}?p={page}"
                res = self.get_with_retry(url)
                if res is None:
                    continue

                soup = BeautifulSoup(res.text, 'html.parser')
                articles = soup.find_all("div", class_="article-content")

                for article in articles:
                    a_tag = article.find('a', href=True)
                    title_tag = article.find('h2', class_='article-title')
                    if not a_tag or not title_tag:
                        continue

                    link = a_tag['href']
                    if not link.startswith("http"):
                        link = "https://dantri.com.vn" + link

                    title = title_tag.get_text(strip=True)
                    content, author, cat, sub_cat_article, date_raw = self.get_article_details(link)

                    if not content:
                        continue
                    if not self.is_today(date_raw):
                        continue

                    article_id = f"DANTRI_{today_str}_{article_counter:05d}"
                    article_counter += 1

                    article_data = {
                        'id': article_id,
                        'title': title,
                        'link': link,
                        'content': content,
                        'date': date_raw,
                        'author': author,
                        'category': cat or main_cat,
                        'sub_category': sub_cat_article or sub_cat,
                        'source': 'Dân Trí'
                    }

                    self.save_to_csv([article_data])
                    time.sleep(4)  # delay lâu hơn tránh bị chặn

    def save_to_csv(self, data):
        try:
            output_dir = os.path.dirname(self.output_csv)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            df = pd.DataFrame(data)
            df.to_csv(self.output_csv, index=False, mode='a', header=not os.path.exists(self.output_csv))
            print(f"[+] Đã lưu {len(df)} dòng vào {self.output_csv}")
        except Exception as e:
            print(f"[!] Lỗi khi lưu CSV: {e}")
