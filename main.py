import json
import logging
import multiprocessing as mp
import pathlib

from crawler import Crawler, CrawlDataEncoder
import config

logger = logging.getLogger(config.LOGGER_NAME)

DEPTH = 0


def worker(site_url: str, queue: mp.Queue) -> None:
    crawler = Crawler(site_url, headless=True)

    # result = crawler.compliance_algo(DEPTH)
    result = crawler.classification_algo()

    queue.put(result)


def main():
    pathlib.Path(config.CRAWL_PATH).mkdir(parents=True, exist_ok=True)

    logger.setLevel(logging.DEBUG)

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

    # All OneTrust sites
    # with open("inputs/sites/results-cmp_name-annotated.json") as log_file:
    #     results = json.load(log_file)
    #     for path in results:
    #         if CMP.ONETRUST in results[path]["cmp_names"]:
    #             site = os.path.basename(os.path.normpath(path))
    #             sites.append(site)

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
