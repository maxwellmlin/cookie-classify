import os
from multiprocessing.pool import ThreadPool
import json

from crawler import Crawler, CrawlData
import utils


def worker(data_path: str, site_url: str, depth: int) -> CrawlData:
    crawler = Crawler(data_path)
    ret = crawler.crawl(site_url, depth)
    crawler.quit()

    return ret


def main():
    DEPTH = 1
    SITE_LIST_PATH = "inputs/sites/sites.txt"  # Path to list of sites to crawl
    CRAWL_NAME = "depth1_noquery"
    crawl_path = f"crawls/{CRAWL_NAME}/"

    if not os.path.exists(crawl_path):
        os.mkdir(crawl_path)

    # Read sites from file
    sites = []
    with open(SITE_LIST_PATH) as file:
        for line in file:
            sites.append(line.strip())

    # Create input for pool
    input_ = []
    for site_url in sites:
        data_path = f"{crawl_path}{utils.get_domain(site_url)}/"
        input_.append((data_path, f"https://{site_url}", DEPTH))

    if num_cpus := os.cpu_count():
        num_threads = num_cpus - 1
    else:
        num_threads = 1
    print("num_threads:", num_threads)
    pool = ThreadPool(num_threads)
    data: dict[str, CrawlData] = {}

    # Run pool
    for result in pool.starmap(worker, input_):
        key: str = result.pop('data_path')  # type: ignore
        data[key] = result

    # Write results to file
    with open(crawl_path + 'results.json', 'w') as file:
        json.dump(data, file)


if __name__ == "__main__":
    main()
