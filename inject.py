import config
import json
from filelock import FileLock

SITES_TO_INJECT = ["weather.com"]
print(SITES_TO_INJECT)

if input("This is a destructive action if you are injecting duplicates. Are you sure you want to continue? (y/n) ") != "y":
    print("Exiting.")
    exit(0)


queue_lock = FileLock(config.QUEUE_PATH + '.lock', timeout=10)

with queue_lock:
    with open(config.QUEUE_PATH, 'r') as file:
        sites = json.load(file)
    
    sites[:0] = SITES_TO_INJECT
    
    with open(config.QUEUE_PATH, 'w') as file:
        json.dump(sites, file)

print("Injection complete.")