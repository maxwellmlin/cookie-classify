import json
import logging
import multiprocessing as mp
import os
from filelock import FileLock
from signal import signal, SIGTERM
import sys
import time

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
    logger.info(f"Starting crawl for '{domain}'.")
    crawler = Crawler(domain, headless=True, wait_time=config.WAIT_TIME)
    def before_exit(*args):
        crawler.driver.quit()

        crawler.results["SIGTERM"] = True
        queue.put(crawler.results)

        sys.exit(0)

    signal(SIGTERM, before_exit)

    # result = crawler.compliance_algo(config.DEPTH)
    result = crawler.classification_algo(total_actions=config.TOTAL_ACTIONS, clickstream_length=config.CLICKSTREAM_LENGTH)

    queue.put(result)

def main():
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")

    log_file = logging.FileHandler(f'{config.DATA_PATH}/{SLURM_ARRAY_TASK_ID}.log', 'a')
    log_file.setLevel(logging.DEBUG)
    log_file.setFormatter(formatter)
    logger.addHandler(log_file)

    # Create input for pool
    output = mp.Queue()
    data = {}

    results_lock = FileLock(config.RESULTS_PATH + '.lock', timeout=10)
    queue_lock = FileLock(config.QUEUE_PATH + '.lock', timeout=10)

    while True:
        start_time = time.time()
        
        # Get next site to crawl
        with queue_lock:
            with open(config.QUEUE_PATH, 'r') as file:
                sites = json.load(file)
                if len(sites) == 0:
                    logger.info("Queue is empty, exiting.")
                    break
                domain = sites.pop(0)
            with open(config.QUEUE_PATH, 'w') as file:
                json.dump(sites, file)
                
        process = mp.Process(target=worker, args=(domain, output))
        process.start()
        
        TIMEOUT = 60 * 60  # 1 hour
        process.join(TIMEOUT)
        logger.info(f"Joining process for '{domain}'.")
        
        sigkill = False
        if process.exitcode is None:
            logger.warn(f"Terminating process for '{domain}' due to timeout.")
            process.terminate()
            process.join()
            
            time.sleep(60)
            if process.exitcode is None:
                logger.critical(f"SIGTERM failed, escalating to SIGKILL.")
                process.kill()
                process.join()
                
                sigkill = True


        result: CrawlResults
        if not sigkill:
            try:
                result = output.get(timeout=60)
            except mp.queues.Empty:
                logger.critical(f"Queue for '{domain}' is empty.")
                result = {
                    "data_path": f"{config.DATA_PATH}{domain}/",
                    "SIGKILL": True,
                }
        else:
            result = {
                "data_path": f"{config.DATA_PATH}{domain}/",
                "SIGKILL": True,
            }
            
        result['SLURM_ARRAY_TASK_ID'] = SLURM_ARRAY_TASK_ID
        result['total_time'] = time.time() - start_time

        # Read existing data, update it, and write back
        with results_lock:
            with open(config.RESULTS_PATH, 'r') as f:
                data = json.load(f)

        data[domain] = result

        with results_lock:
            with open(config.RESULTS_PATH, 'w') as f:
                json.dump(data, f, cls=CrawlDataEncoder)

if __name__ == "__main__":    
    main()
