from bs4 import BeautifulSoup
import requests
from typing import List, Dict, Optional
from datetime import datetime
from .base import BaseCrawler
from crawlers.utils.io import save_raw_data, save_processed_data
from crawlers.utils.preprocess import preprocess_data
from crawlers.utils.cleaner import clean_text
from crawlers.utils.dater import normalize_date
import time
import logging
import os
import pandas as pd

class VNExpressCrawler(BaseCrawler):
    def __init__(self):
        super().__init__()
        self.source = 'vnexpress'
        self.base_url = 'https://vnexpress.net'

    def fetch_categories(self) -> Dict[str, Dict]:
        """Fetch all categories and subcategories from the homepage"""
        res = requests.get(self.base_url)
        soup = BeautifulSoup(res.text, 'html.parser')
        menu_items = soup.find_all('li', attrs={'data-id': True})
        categories: Dict[str, Dict] = {}

        for li in menu_items:
            a_tags = li.find_all('a', recursive=False)
            if not a_tags:
                continue

            main_link = a_tags[0]['href']
            main_name = clean_text(a_tags[0].get_text())
            if main_link.startswith('/'):
                main_link = self.base_url + main_link

            categories[main_name] = {'link': main_link, 'subcategories': {}}
            sub_menu = li.find('ul')
            if sub_menu:
                for sub_a in sub_menu.find_all('a'):
                    sub_name = clean_text(sub_a.get_text())
                    sub_link = sub_a['href']
                    if sub_link.startswith('/'):
                        sub_link = self.base_url + sub_link
                    categories[main_name]['subcategories'][sub_name] = sub_link

        return categories

    def fetch_articles(self, category_url: str, page: int = 1) -> List:
        """Fetch articles from a category page"""
        url = category_url if page == 1 else f"{category_url}-p{page}"
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup.find_all('article', class_='item-news')
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return []

    def parse_article(self, article, category: str) -> Optional[Dict]:
        """Parse individual article details"""
        title_tag = article.find('h3', class_='title-news')
        if not title_tag:
            return None

        title = clean_text(title_tag.get_text())
        link = title_tag.find('a')['href']
        if link.startswith('/'):
            link = self.base_url + link

        try:
            resp = requests.get(link)
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Content extraction
            content_div = soup.find('article', class_='fck_detail')
            content = ('\n'.join(p.get_text(strip=True) for p in content_div.find_all('p'))
                       if content_div else '')
            # Date extraction
            time_tag = soup.find('span', class_='date')
            date_str = time_tag.get_text(strip=True) if time_tag else ''
            date = normalize_date(date_str) if date_str else datetime.now()
            # Author extraction
            author = None
            for p in reversed(soup.find_all('p', class_='Normal')):
                strong = p.find('strong')
                if strong:
                    author = clean_text(strong.get_text())
                    break

            return {
                'title': title,
                'link': link,
                'content': content,
                'date': date,
                'author': author,
                'category': category,
                'source': self.source
            }
        except Exception as e:
            self.logger.error(f"Error parsing {link}: {e}")
            return None

    def crawl(self, num_pages: int = 1, max_articles: int = 5) -> List[Dict]:
        """Main method to crawl and optionally save raw and processed data"""
        data: List[Dict] = []
        categories = self.fetch_categories()
        article_count = 0

        for category, info in categories.items():
            self.logger.info(f"Crawling category: {category}")
            for page in range(1, num_pages + 1):
                for art in self.fetch_articles(info['link'], page):
                    if article_count >= max_articles:
                        break
                    parsed = self.parse_article(art, category)
                    if parsed:
                        data.append(parsed)
                        article_count += 1
                    time.sleep(1)
                if article_count >= max_articles:
                    break
            if article_count >= max_articles:
                break

            for sub_name, sub_link in info['subcategories'].items():
                self.logger.info(f"Crawling subcategory: {sub_name}")
                for page in range(1, num_pages + 1):
                    for art in self.fetch_articles(sub_link, page):
                        if article_count >= max_articles:
                            break
                        parsed = self.parse_article(art, f"{category}/{sub_name}")
                        if parsed:
                            data.append(parsed)
                            article_count += 1
                        time.sleep(1)
                    if article_count >= max_articles:
                        break
                if article_count >= max_articles:
                    break
            if article_count >= max_articles:
                break
        save_raw_data(data)
        df = pd.DataFrame(data)
        df2 = preprocess_data(df)
        save_processed_data(df2)

        print(f"✅ Crawling finished. Total articles crawled: {article_count}")

        return data