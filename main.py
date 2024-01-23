import json
import logging
import multiprocessing as mp
import pathlib
import os
import argparse
from filelock import Timeout, FileLock

from crawler import Crawler, CrawlDataEncoder
import config

logger = logging.getLogger(config.LOGGER_NAME)


def worker(site_url: str, queue: mp.Queue) -> None:
    crawler = Crawler(site_url, headless=True)

    # result = crawler.compliance_algo(config.DEPTH)
    result = crawler.classification_algo(num_clickstreams=10, clickstream_length=5, control_screenshots=5)
    # result = crawler.classification_algo(num_clickstreams=1, clickstream_length=1, control_screenshots=1)

    queue.put(result)


def main(jobs=1):
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

    SLURM_ARRAY_TASK_ID = int(os.getenv('SLURM_ARRAY_TASK_ID'))
    print("SLURM_ARRAY_TASK_ID:", SLURM_ARRAY_TASK_ID)

    results_path = config.CRAWL_PATH + 'results.json'
    with open(results_path, 'w') as results:
        results.write("{}")

    lock_path = results_path + '.lock'

    lock = FileLock(lock_path, timeout=1)

    for i in range(SLURM_ARRAY_TASK_ID-1, len(sites), jobs):
        process = mp.Process(target=worker, args=(f"https://{sites[i]}", output))
        process.start()

        result = output.get()

        # Read existing data, update it, and write back
        with lock:
            with open(results_path, 'r') as results:
                data = json.load(results)

        key = result.pop('url')
        data[key] = result

        with lock:
            with open(results_path, 'w') as results:
                json.dump(data, results, cls=CrawlDataEncoder)

        process.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start a crawl.")
    parser.add_argument(
        '--jobs',
        type=int,
        help="Number of jobs to create."
    )
    args = parser.parse_args()
    
    main(jobs=args.jobs)
