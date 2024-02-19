CRAWL_NAME = f"queue-test"  # Name of crawl
SITE_LIST_PATH = "inputs/sites/sites.txt"  # Path to list of sites to crawl
DEPTH = 0
WAIT_TIME = 5

TOTAL_ACTIONS = 50
CLICKSTREAM_LENGTH = 5

DATA_PATH = f"/usr/project/xtmp/mml66/cookie-classify/{CRAWL_NAME}/"
LOGGER_NAME = CRAWL_NAME
RESULTS_PATH = DATA_PATH + "results.json"
QUEUE_PATH = DATA_PATH + "queue.json"
CONFIG_PATH = DATA_PATH + "config.yaml"