import config
import json
from filelock import FileLock

SITES_TO_INJECT = [
    "maxwellmlin.com"
]

queue_path = config.DATA_PATH + 'queue.json'  # where to store results for individual sites
queue_lock = FileLock(queue_path + '.lock', timeout=10)

with queue_lock:
    with open(queue_path, 'r') as file:
        sites = json.load(file)
    
    sites[:0] = SITES_TO_INJECT
    
    with open(queue_path, 'w') as file:
        json.dump(sites, file)