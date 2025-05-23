from abc import ABC, abstractmethod
import logging

class BaseCrawler(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def crawl(self, max_articles: int = None, num_pages: int = 1):
        """Main method to perform crawling"""
        pass

    def save_to_db(self, data):
        pass

    def save_to_file(self, data, filepath):
        pass
