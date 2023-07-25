import os
from multiprocessing.pool import ThreadPool
import json

from crawler import Crawler
import utils
from crawler import CrawlData


def worker(data_path: str, site_url: str, depth: int) -> CrawlData:
    crawler = Crawler(data_path)
    ret = crawler.crawl(site_url, depth)
    crawler.quit()

    return ret


SITE_LIST_PATH = "inputs/sites/sites.txt"  # Path to list of sites to crawl
CRAWL_NAME = "cmp"
crawl_path = f"crawls/{CRAWL_NAME}/"

if not os.path.exists(crawl_path):
    os.mkdir(crawl_path)

# Get list of sites to crawl
sites = []
with open(SITE_LIST_PATH) as file:
    for line in file:
        sites.append(line.strip())

input = []
for site_url in sites:
    # TODO: this is a temp fix for detectedBanner.txt
    site_url = f"https://{site_url}"

    # Create data folder
    data_path = f"{crawl_path}{utils.get_domain(site_url)}/"

    input.append((data_path, site_url, 0))

    # See https://stackoverflow.com/a/1316799/ for why we need to use multiprocessing
    # process = mp.Process(target=worker, args=(data_path, site_url, 0))
    # process.start()
    # process.join()

num_threads = os.cpu_count() or 1
pool = ThreadPool(num_threads)
data: dict[str, CrawlData] = {}

for result in pool.starmap(worker, input):
    key = result.pop('data_path')
    data[key] = result

with open(crawl_path + 'results.json', 'w') as file:
    json.dump(data, file)
