import config
import json
from filelock import FileLock

SITES_TO_INJECT = [
    "maxwellmlin.com"
]

queue_lock = FileLock(config.QUEUE_PATH + '.lock', timeout=10)

with queue_lock:
    with open(config.QUEUE_PATH, 'r') as file:
        sites = json.load(file)
    
    sites[:0] = SITES_TO_INJECT
    
    with open(config.QUEUE_PATH, 'w') as file:
        json.dump(sites, file)