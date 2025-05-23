from crawlers.vnexpress import VNExpressCrawler
from crawlers.tienphong import TienPhongCrawler

def main():
    # Crawl VNExpress
    print("Starting VNExpress crawl...")
    vn_crawler = VNExpressCrawler()
    vn_data = vn_crawler.crawl(num_pages=1, max_articles=5)
    print(f"VNExpress: {len(vn_data)} articles crawled")

    # Crawl Tiền Phong
    print("Starting Tiền Phong crawl...")
    tp_crawler = TienPhongCrawler()
    tp_data = tp_crawler.crawl(pages=1, max_articles=5)
    print(f"Tiền Phong: {len(tp_data)} articles crawled")

if __name__ == '__main__':
    main()
