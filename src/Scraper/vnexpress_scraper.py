from base_scraper import BaseScraper
import requests
from bs4 import BeautifulSoup
import time
import os
import pandas as pd
from datetime import datetime

class VNExpressScraper(BaseScraper):
    def __init__(self, headle, base_url, output_csv, original_csv):
        super().__init__(headle, base_url, output_csv, original_csv)

    def get_categories(self):
        url = 'https://vnexpress.net'
        try:
            res = requests.get(url, timeout=10)
        except Exception as e:
            print(f"[!] Không thể kết nối tới trang chủ: {e}")
            return []

        soup = BeautifulSoup(res.text, 'html.parser')
        menu_items = soup.find_all('li', attrs={'data-id': True})
        categories = []

        for li in menu_items:
            a_tag = li.find('a')
            if a_tag and 'href' in a_tag.attrs:
                main_category = a_tag.get_text(strip=True)
                main_link = a_tag['href']
                if main_link.startswith('/'):
                    main_link = 'https://vnexpress.net' + main_link

                categories.append((main_category, None, main_link))

                try:
                    res_sub = requests.get(main_link, timeout=10)
                    soup_sub = BeautifulSoup(res_sub.text, 'html.parser')
                    ul_main = soup_sub.find('ul', class_='ul-nav-folder')

                    if ul_main:
                        for li in ul_main.find_all('li', recursive=False): 
                            a_tag = li.find('a', href=True)
                            if a_tag:
                                sub_category = a_tag.get_text(strip=True)
                                sub_link = a_tag['href']
                                if sub_link.startswith('/'):
                                    sub_link = 'https://vnexpress.net' + sub_link
                                categories.append((main_category, sub_category, sub_link))

                            sub_ul = li.find('ul', class_='sub-more')
                            if sub_ul:
                                for sub_li in sub_ul.find_all('li'):
                                    sub_a = sub_li.find('a', href=True)
                                    if sub_a:
                                        sub_name = sub_a.get_text(strip=True)
                                        sub_link = sub_a['href']
                                        if sub_link.startswith('/'):
                                            sub_link = 'https://vnexpress.net' + sub_link
                                        categories.append((main_category, sub_name, sub_link))
                except Exception as e:
                    print(f"[!] Lỗi khi truy cập chuyên mục {main_category}: {e}")
                time.sleep(0.5)

        print(f"[+] Tìm thấy {len(categories)} chuyên mục & tiểu mục")
        print(categories)
        return categories

    def scrape(self):
        print("[+] Bắt đầu crawl VNExpress...")
        categories = self.get_categories()
        article_counter = 1
        today = datetime.now().strftime("%-d/%-m/%Y")
        today_str = datetime.now().strftime("%d%m%y")

        for main_cat, sub_cat, base_url in categories:
            for page in range(1, 6):
                url = base_url if page == 1 else f"{base_url}-p{page}"
                try:
                    response = requests.get(url)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    articles = soup.find_all('article', class_='item-news')
                except:
                    continue

                for article in articles:
                    title_tag = article.find('h3', class_='title-news')
                    if not title_tag:
                        continue

                    title = title_tag.get_text(strip=True)
                    link = title_tag.find('a')['href']
                    try:
                        article_res = requests.get(link)
                        article_soup = BeautifulSoup(article_res.text, 'html.parser')

                        # Lấy sub_category từ meta
                        meta_folder = article_soup.find('meta', attrs={'name': 'tt_list_folder_name'})
                        if meta_folder and 'content' in meta_folder.attrs:
                            folder_parts = meta_folder['content'].split(',')
                            if len(folder_parts) >= 3:
                                sub_cat = folder_parts[2].strip()

                        time_tag = article_soup.find('span', class_='date')
                        date_raw = time_tag.get_text(strip=True) if time_tag else None
                        if not date_raw:
                            continue

                        try:
                            date_parts = date_raw.split(',')
                            if len(date_parts) >= 2:
                                date_clean = date_parts[1].strip()
                            else:
                                continue
                        except:
                            continue

                        if date_clean != today:
                            continue

                        content_div = article_soup.find('article', class_='fck_detail')
                        content_text = '\n'.join([p.get_text(strip=True) for p in content_div.find_all('p')]) if content_div else None
                        if not content_text or len(content_text) < 30:
                            continue

                        author = None
                        normal_paragraphs = article_soup.find_all('p', class_='Normal')
                        for p in reversed(normal_paragraphs):
                            strong_tag = p.find('strong')
                            if strong_tag:
                                author = strong_tag.get_text(strip=True)
                                break

                        article_id = f"VNEX_{today_str}_{article_counter:05d}"
                        article_counter += 1

                        article_data = {
                            'id': article_id,
                            'title': title,
                            'link': link,
                            'content': content_text,
                            'date': date_raw,
                            'author': author,
                            'category': main_cat,
                            'sub_category': sub_cat,
                            'source': 'VN Express'
                        }

                        self.save_to_csv([article_data])

                    except:
                        continue

                    time.sleep(1)

    def save_to_csv(self, data):
        try:
            os.makedirs(os.path.dirname(self.output_csv), exist_ok=True)
            df = pd.DataFrame(data)
            df.to_csv(self.output_csv, index=False, mode='a', header=not os.path.exists(self.output_csv))
            print(f"[+] Đã lưu {len(df)} dòng vào {self.output_csv}")
        except Exception as e:
            print(f"[!] Lỗi khi lưu CSV: {e}")
