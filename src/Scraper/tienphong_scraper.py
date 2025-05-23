import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
import os
from datetime import datetime
from base_scraper import BaseScraper

class TienPhongScraper(BaseScraper):
    def __init__(self, headle, base_url, output_csv, original_csv):
        super().__init__(headle, base_url, output_csv, original_csv)

    def get_categories(self):
        categories = {}
        res = requests.get(self.base_url)
        soup = BeautifulSoup(res.text, 'html.parser')
        menu_items = soup.find_all('li', attrs={'data-id': True})

        for li in menu_items:
            a_tag = li.find('a')
            if a_tag and 'href' in a_tag.attrs:
                name = a_tag.get_text(strip=True)
                link = a_tag['href']
                if link.startswith('/'):
                    link = 'https://tienphong.vn' + link
                categories[name] = link
        return categories

    def save_to_csv(self, articles):
        df = pd.DataFrame(articles)
        write_header = not os.path.exists(self.output_csv) or os.path.getsize(self.output_csv) == 0
        df.to_csv(self.output_csv, index=False, mode='a', header=write_header)
        print(f"\n✅ Đã lưu {len(articles)} bài viết vào: {self.output_csv}")

    def scrape(self):
        seen_links = set()
        categories = self.get_categories()
        num_pages = 5
        today = datetime.now().strftime("%d/%m/%Y")
        today_str = datetime.now().strftime("%d%m%y")
        article_counter = 1

        for category, base_url in categories.items():
            print(f"🔍 Đang lấy category: {category}")
            for page in range(1, num_pages + 1):
                url = base_url if page == 1 else f"{base_url}-p{page}"
                print(f"   → Page {page}: {url}")
                try:
                    response = requests.get(url, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    articles = soup.find_all('article', class_='story')
                except Exception as e:
                    print(f"⚠️  Lỗi khi lấy danh sách bài viết: {e}")
                    continue

                current_articles = []
                for article in articles:
                    try:
                        heading_tag = article.find(['h2', 'h3'], class_='story__heading')
                        link_tag = heading_tag.find('a', class_='cms-link') if heading_tag else None
                        if not link_tag:
                            continue

                        link = link_tag['href']
                        if link in seen_links:
                            continue
                        seen_links.add(link)

                        title = link_tag.get_text(strip=True)

                        # Truy cập từng bài viết
                        article_res = requests.get(link, timeout=10)
                        article_soup = BeautifulSoup(article_res.text, 'html.parser')

                        time_tag = article_soup.find('span', class_='time')
                        date = time_tag.get_text(strip=True) if time_tag else None
                        if not date:
                            continue
                        date_clean = date.split('|')[0].strip()
                        if date_clean != today:
                            continue

                        content_div = article_soup.find('div', class_='col-27 article-content')
                        content_text = '\n'.join([p.get_text(strip=True) for p in content_div.find_all('p')]) if content_div else None
                        if not content_text or len(content_text.strip()) < 30:
                            continue

                        # Tác giả
                        author = None
                        author_tag_1 = article_soup.find('div', class_='article__author')
                        if author_tag_1:
                            name_tag = author_tag_1.find('span', class_='name cms-author')
                            if name_tag:
                                author = name_tag.get_text(strip=True)

                        if not author:
                            author_tag_2 = article_soup.find('span', class_='author')
                            if author_tag_2:
                                cms_author = author_tag_2.find('a', class_='cms-author')
                                if cms_author:
                                    name_span = cms_author.find('span')
                                    if name_span:
                                        author = name_span.get_text(strip=True)

                        cat_main, sub_cat = category, None
                        if ' > ' in category:
                            cat_main, sub_cat = category.split(' > ', 1)

                        current_articles.append({
                            'id': f"TP_{today_str}_{article_counter:05d}",
                            'title': title,
                            'link': link,
                            'content': content_text,
                            'date': date,
                            'author': author,
                            'category': cat_main,
                            'sub_category': sub_cat,
                            'source': 'Tiền Phong'
                        })
                        article_counter += 1
                        time.sleep(1.5)
                    except Exception as e:
                        print(f"⚠️  Lỗi khi xử lý bài viết: {e}")
                        continue

                self.articles.extend(current_articles)
                self.save_to_csv(current_articles)
