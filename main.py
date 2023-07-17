import os

from crawler import Crawler
import utils

import multiprocessing as mp


def worker(data_path, site_url, depth):
    crawler = Crawler(data_path)
    crawler.crawl(site_url, depth)
    crawler.quit()


SITE_LIST_PATH = "inputs/sites/detectedBanner.txt"  # Path to list of sites to crawl

if not os.path.exists("crawls"):
    os.mkdir("crawls")

# Get list of sites to crawl
sites = []
with open(SITE_LIST_PATH) as file:
    for line in file:
        sites.append(line.strip())

with mp.Pool(processes=mp.cpu_count()) as pool:
    processes = []

    for site_url in sites:
        # TODO: this is a temp fix for detectedBanner.txt
        site_url = f"https://{site_url}"

        # Create data folder
        data_path = f"crawls/{utils.get_domain(site_url)}/"

        args = (data_path, site_url, 2)
        processes.append(args)

    pool.starmap(worker, processes)
