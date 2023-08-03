import os

from crawler import Crawler, InteractionType
import utils

import multiprocessing as mp


def worker(data_path, site_url, depth):
    no_action_crawler = Crawler(data_path)
    no_action_crawler.crawl(site_url, depth, InteractionType.NO_ACTION)
    no_action_crawler.quit()
    accept_crawler = Crawler(data_path)
    accept_crawler.crawl(site_url, depth, InteractionType.ACCEPT)
    accept_crawler.quit()
    reject_crawler = Crawler(data_path)
    reject_crawler.crawl(site_url, depth, InteractionType.REJECT)
    reject_crawler.quit()

SITE_LIST_PATH = "inputs/sites/detectedBanner.txt"  # Path to list of sites to crawl

if not os.path.exists("crawls/full_requests5"):
    os.mkdir("crawls/full_requests5")

# Get list of sites to crawl
sites = []
with open(SITE_LIST_PATH) as file:
    for line in file:
        sites.append(line.strip())

for site_url in sites:
    # TODO: this is a temp fix for detectedBanner.txt
    site_url = f"https://{site_url}"

    # Create data folder
    data_path = f"crawls/full_requests5/{utils.get_domain(site_url)}/"

    # See https://stackoverflow.com/a/1316799/ for why we need to use multiprocessing
    process = mp.Process(target=worker, args=(data_path, site_url, 0))
    process.start()
    process.join()
