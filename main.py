import os

from crawler import Crawler
import utils

import multiprocessing as mp


def worker(data_path, site_url, depth):
    crawler = Crawler(data_path)
    crawler.crawl(site_url, depth)
    crawler.quit()


SITE_LIST_PATH = "inputs/sites/sites.txt"  # Path to list of sites to crawl

if not os.path.exists("crawls"):
    os.mkdir("crawls")

# Get list of sites to crawl
sites = []
with open(SITE_LIST_PATH) as file:
    for line in file:
        sites.append(line.strip())

for site_url in sites:
    # Create data folder
    data_path = f"crawls/{utils.get_domain(site_url)}/"
    if not os.path.exists(data_path):
        os.mkdir(data_path)

    # TODO: this is a temp fix for detectedBanner.txt
    site_url = f"https://{site_url}"

    # See https://stackoverflow.com/a/1316799/ for why we need to use multiprocessing
    process = mp.Process(target=worker, args=(data_path, site_url, 0))
    process.start()
    process.join()
