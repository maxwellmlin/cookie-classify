import json
import logging
import multiprocessing as mp
import pathlib

from crawler import Crawler, CrawlDataEncoder
import config

logger = logging.getLogger(config.LOGGER_NAME)


def worker(site_url: str, queue: mp.Queue) -> None:
    crawler = Crawler(site_url, headless=True, time_to_wait=10)

    # result = crawler.compliance_algo(config.DEPTH)
    result = crawler.classification_algo(num_clickstreams=10, clickstream_length=5, control_screenshots=5)

    queue.put(result)


def main():
    pathlib.Path(config.CRAWL_PATH).mkdir(parents=True, exist_ok=True)

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")

    log_stream = logging.StreamHandler()
    log_stream.setLevel(logging.DEBUG)
    log_stream.setFormatter(formatter)

    log_file = logging.FileHandler(f'{config.CRAWL_PATH}/crawl.log', 'a')
    log_file.setLevel(logging.DEBUG)
    log_file.setFormatter(formatter)

    logger.addHandler(log_stream)
    logger.addHandler(log_file)

    sites = []

    # Read sites from text file
    with open(config.SITE_LIST_PATH) as file:
        for line in file:
            sites.append(line.strip())

    # Create input for pool
    output = mp.Queue()
    data = {}
    for site_url in sites:
        process = mp.Process(target=worker, args=(f"https://{site_url}", output))
        process.start()

        result = output.get()
        key = result.pop('data_path')
        data[key] = result

        with open(config.CRAWL_PATH + 'results.json', 'w') as log_file:
            json.dump(data, log_file, cls=CrawlDataEncoder)

        process.join()


if __name__ == "__main__":
    main()
