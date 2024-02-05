import json
import logging
import multiprocessing as mp
import pathlib
import os
import argparse
from filelock import Timeout, FileLock

from crawler import Crawler, CrawlDataEncoder, CrawlResults
import config

logger = logging.getLogger(config.LOGGER_NAME)
SLURM_ARRAY_TASK_ID = int(os.getenv('SLURM_ARRAY_TASK_ID')) # type: ignore

def worker(domain: str, queue: mp.Queue) -> None:
    """
    We need to use multiprocessing to explicitly free up memory after each crawl.
    See https://stackoverflow.com/questions/38164635/selenium-not-freeing-up-memory-even-after-calling-close-quit
    for more details.
    """    
    crawler = Crawler(domain, headless=True, time_to_wait=config.TIME_TO_WAIT)

    # result = crawler.compliance_algo(config.DEPTH)
    result = crawler.classification_algo(num_clickstreams=config.NUM_CLICKSTREAMS, clickstream_length=config.CLICKSTREAM_LENGTH)

    queue.put(result)

def main(jobs=1):
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")

    log_stream = logging.StreamHandler()
    log_stream.setLevel(logging.DEBUG)
    log_stream.setFormatter(formatter)
    logger.addHandler(log_stream)

    log_file = logging.FileHandler(f'{config.CRAWL_PATH}/{SLURM_ARRAY_TASK_ID}.log', 'a')
    log_file.setLevel(logging.DEBUG)
    log_file.setFormatter(formatter)
    logger.addHandler(log_file)

    logger.info(f"SLURM_ARRAY_TASK_ID: {SLURM_ARRAY_TASK_ID}")

    # Read sites from text file
    sites = []
    with open(config.SITE_LIST_PATH) as file:
        for line in file:
            sites.append(line.strip())

    # Create input for pool
    output = mp.Queue()
    data = {}

    sites_path = config.CRAWL_PATH + 'sites.json'  # where to store results for individual sites
    sites_lock = FileLock(sites_path + '.lock', timeout=10)

    for i in range(SLURM_ARRAY_TASK_ID-1, len(sites), jobs):
        crawl_domain = sites[i]
        
        process = mp.Process(target=worker, args=(crawl_domain, output))
        process.start()

        result: CrawlResults = output.get()

        # Read existing data, update it, and write back
        with sites_lock:
            with open(sites_path, 'r') as results:
                data = json.load(results)

        result['SLURM_ARRAY_TASK_ID'] = SLURM_ARRAY_TASK_ID
        
        data[crawl_domain] = result

        with sites_lock:
            with open(sites_path, 'w') as results:
                json.dump(data, results, cls=CrawlDataEncoder)

        process.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--jobs',
        type=int,
        required=True
    )
    args = parser.parse_args()
    
    main(jobs=args.jobs)
