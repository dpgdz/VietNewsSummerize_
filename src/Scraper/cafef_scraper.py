import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from base_scraper import BaseScraper

class CafeFScraper(BaseScraper):
    def __init__(self, headle, base_url, output_csv, original_csv, persistent_file, emb_csv):
        super().__init__(headle, base_url, output_csv, original_csv, persistent_file, emb_csv)

    def get_categories(self):
        res = requests.get(self.base_url)
        soup = BeautifulSoup(res.text, 'html.parser')
        menu_div = soup.find('div', class_='menucategory menuheader header__nav', id='menu_wrap')
        menu_items = menu_div.find_all('li', class_='acvmenu') if menu_div else []

        categories = {}
        for li in menu_items:
            a_tag = li.find('a')
            if a_tag and 'href' in a_tag.attrs:
                name = a_tag.get_text(strip=True)
                link = a_tag['href']
                if link.startswith('/'):
                    link = self.base_url + link
                if name:
                    categories[name] = link
        return categories

    def save_to_csv(self):
        df = pd.DataFrame(self.articles)
        df.to_csv(self.output_csv, index=False)
        print(f"\n✅ Đã lưu {len(self.articles)} bài viết vào: {self.output_csv}")

    def scrape(self, num_clicks=1):
        self.articles = []
        article_counter = 1
        #categories = self.get_categories()
        categories = {'CHỨNG KHOÁN': 'https://cafef.vn/thi-truong-chung-khoan.chn'}

        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        for category, base_url in categories.items():
            print(f"\n=== 📂 Crawling chuyên mục: {category.upper()} ===")
            driver.get(base_url)
            wait = WebDriverWait(driver, 10)

            for i in range(num_clicks):
                try:
                    button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-viewmore")))
                    driver.execute_script("arguments[0].click();", button)
                    print(f"🔄 Đã bấm 'Xem thêm' lần {i + 1}")
                    time.sleep(2)
                except:
                    print("⚠️ Không thể bấm nút 'Xem thêm' nữa.")
                    break

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            articles = soup.find_all('div', class_='tlitem box-category-item')
            print(f"📰 Tìm thấy {len(articles)} bài viết:")

            for article in articles:
                h3_tag = article.find('h3')
                a_tag = h3_tag.find('a') if h3_tag else None
                if a_tag and 'href' in a_tag.attrs:
                    title = a_tag.get_text(strip=True)
                    link = a_tag['href']
                    if link.startswith('/'):
                        link = self.base_url + link
                    print(f"- {title}: {link}")

                    try:
                        article_res = requests.get(link)
                        article_soup = BeautifulSoup(article_res.text, 'html.parser')

                        content_div = article_soup.find('div', class_='contentdetail')
                        content_text = None
                        if content_div:
                            paragraphs = content_div.find_all('p')
                            content_text = '\n'.join([p.get_text(strip=True) for p in paragraphs])

                        time_tag = article_soup.find('span', class_='pdate')
                        date = time_tag.get_text(strip=True) if time_tag else None

                        author = None
                        normal_paragraphs = article_soup.find_all('p', class_='Normal')
                        for p in reversed(normal_paragraphs):
                            strong_tag = p.find('strong')
                            if strong_tag:
                                possible_author = strong_tag.get_text(strip=True)
                                if possible_author and len(possible_author.split()) <= 5:
                                    author = possible_author
                                    break

                        if not author:
                            author_tag = article_soup.find('p', class_='author')
                            if author_tag:
                                author = author_tag.get_text(strip=True)

                        article_id = f"CAFEF_{article_counter:05d}"
                        article_counter += 1

                        self.articles.append({
                            'id': article_id,
                            'title': title,
                            'link': link,
                            'content': content_text,
                            'date': date,
                            'author': author,
                            'category': category,
                            'source': 'CafeF'
                        })

                    except Exception as e:
                        print(f"❌ Lỗi bài viết: {e}")

                    time.sleep(1)

        driver.quit()
        self.save_to_csv()
