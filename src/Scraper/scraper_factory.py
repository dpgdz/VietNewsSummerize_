from vnexpress_scraper import VNExpressScraper

def get_scraper(name, headle, base_url, output_csv, process):
    if name == "VNExpress":
        return VNExpressScraper(headle, base_url, output_csv, process)
    else:
        raise ValueError(f"Unknown scraper: {name}")