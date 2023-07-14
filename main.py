import os

from crawler import Crawler
import utils

SITE_LIST_PATH = "inputs/sites/detectedBanner.txt"  # Path to list of sites to crawl

if not os.path.exists("crawls"):
    os.mkdir("crawls")

# Get list of sites to crawl
sites = []
with open(SITE_LIST_PATH) as file:
    for line in file:
        sites.append(line.strip())

for site_url in sites:
    # Create data folder
    data_path = f"./crawls/{utils.get_domain(site_url)}/"
    if not os.path.exists(data_path):
        os.mkdir(data_path)

    # Reinstantiate crawler to clear cookies
    crawler = Crawler(data_path, save_har=True)

    # TODO: this is a temp fix for detectedBanner.txt
    site_url = f"https://{site_url}"

    # Crawl website
    crawler.crawl(site_url, depth=0)

    # Safely close crawler
    crawler.quit()
