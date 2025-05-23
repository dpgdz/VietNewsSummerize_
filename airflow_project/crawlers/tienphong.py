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


class TienPhongCrawler(BaseCrawler):
    def __init__(self):
        super().__init__()
        self.source = 'tienphong'
        self.base_url = 'https://tienphong.vn'

    def fetch_categories(self) -> Dict[str, str]:
        res = requests.get(self.base_url)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.find_all('li', attrs={'data-id': True})
        cats: Dict[str, str] = {}
        for li in items:
            a = li.find('a')
            if a and a.has_attr('href'):
                name = clean_text(a.get_text())
                link = a['href']
                if link.startswith('/'):
                    link = self.base_url + link
                cats[name] = link
        return cats

    def fetch_articles(self, url: str, page: int = 1) -> List:
        target = url if page == 1 else f"{url}-p{page}"
        try:
            r = requests.get(target)
            soup = BeautifulSoup(r.text, 'html.parser')
            return soup.find_all('article', class_='story')
        except Exception as e:
            self.logger.error(f"Error fetching {target}: {e}")
            return []

    def parse_article(self, art, cat: str) -> Optional[Dict]:
        heading = art.find(['h2', 'h3'], class_='story__heading')
        lt = heading.find('a', class_='cms-link') if heading else None
        if not lt:
            return None
        link = lt['href']
        if link.startswith('/'):
            link = self.base_url + link
        title = clean_text(lt.get_text())
        try:
            r = requests.get(link)
            s = BeautifulSoup(r.text, 'html.parser')
            cdiv = s.find('div', class_='col-27 article-content')
            content = '\n'.join(p.get_text(strip=True) for p in cdiv.find_all('p')) if cdiv else ''
            tt = s.find('span', class_='time')
            ds = tt.get_text(strip=True) if tt else ''
            date = normalize_date(ds) if ds else datetime.now()
            author = None
            a1 = s.find('div', class_='article__author')
            if a1:
                na = a1.find('span', class_='name cms-author')
                if na:
                    author = clean_text(na.get_text())
            if not author:
                a2 = s.find('span', class_='author')
                if a2:
                    ca = a2.find('a', class_='cms-author')
                    if ca and ca.find('span'):
                        author = clean_text(ca.find('span').get_text())
            return {'title': title, 'link': link, 'content': content,
                    'date': date, 'author': author,
                    'category': cat, 'source': self.source}
        except Exception as e:
            self.logger.error(f"Error parsing {link}: {e}")
            return None

    def crawl(self, pages: int = 1, max_articles: int = 5) -> List[Dict]:
        data = []
        cats = self.fetch_categories()
        article_count = 0

        for cat, url in cats.items():
            self.logger.info(f"Crawling {cat}")
            for pg in range(1, pages + 1):
                for art in self.fetch_articles(url, pg):
                    if article_count >= max_articles:
                        break
                    p = self.parse_article(art, cat)
                    if p:
                        data.append(p)
                        article_count += 1
                    time.sleep(1)
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