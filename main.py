import json
import logging
import multiprocessing as mp
import pathlib

from crawler import Crawler, CrawlData
import utils
import config

logger = logging.getLogger(config.LOGGER_NAME)

DEPTH = 0
SITE_LIST_PATH = "inputs/sites/detectedBanner.txt"  # Path to list of sites to crawl
CRAWL_PATH = "crawls/cmp_detection/"


def worker(data_path: str, site_url: str, depth: int, queue: mp.Queue) -> None:
    crawler = Crawler(data_path)
    ret = crawler.crawl(site_url, depth)
    crawler.cleanup_driver()

    queue.put(ret)


def main():
    pathlib.Path(CRAWL_PATH).mkdir(parents=True, exist_ok=True)

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")

    log_stream = logging.StreamHandler()
    log_stream.setLevel(logging.DEBUG)
    log_stream.setFormatter(formatter)

    log_file = logging.FileHandler(f'{CRAWL_PATH}/crawl.log', 'a')
    log_file.setLevel(logging.DEBUG)
    log_file.setFormatter(formatter)

    logger.addHandler(log_stream)
    logger.addHandler(log_file)

    # Read sites from file
    sites = []
    with open(SITE_LIST_PATH) as log_file:
        for line in log_file:
            sites.append(line.strip())

    # Create input for pool
    output: mp.Queue = mp.Queue()
    data: dict[str, CrawlData] = {}
    for site_url in sites:
        data_path = f"{CRAWL_PATH}{utils.get_domain(site_url)}/"

        process = mp.Process(target=worker, args=(data_path, f"https://{site_url}", DEPTH, output))
        process.start()

        result = output.get()
        key: str = result.pop('data_path')
        data[key] = result
        with open(CRAWL_PATH + 'results.json', 'w') as log_file:
            json.dump(data, log_file)

        process.join()


if __name__ == "__main__":
    main()
