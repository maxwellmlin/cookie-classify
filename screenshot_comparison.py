import os
import pandas as pd
import json
import statistics
from pathlib import Path
import yaml
import matplotlib.pyplot as plt
import matplotlib as mpl
from filelock import FileLock
from crawler import CrawlResults
from utils.utils import get_directories, get_domain
from utils.image_shingle import ImageShingle

##############################################################################

CRAWL_NAME = 'KJ2GW'

DATA_PATH = Path("/usr/project/xtmp/mml66/cookie-classify/") / CRAWL_NAME
ANALYSIS_PATH = Path("analysis") / CRAWL_NAME
ANALYSIS_PATH.mkdir(parents=True, exist_ok=True)

##############################################################################

with open(DATA_PATH / "config.yaml", "r") as stream:
    config = yaml.safe_load(stream)

##############################################################################

# Site list
site_list = []
with open(config["SITE_LIST_PATH"]) as file:
    for line in file:
        site_list.append(line.strip())

# Site queue
queue_lock = FileLock(config["QUEUE_PATH"] + '.lock', timeout=10)
with queue_lock:
    with open(config["QUEUE_PATH"], 'r') as file:
        site_queue = json.load(file)

# Site results
results_lock = FileLock(config["RESULTS_PATH"] + '.lock', timeout=10)
with results_lock:
    with open(config["RESULTS_PATH"]) as file:
        site_results: dict[str, CrawlResults] = json.load(file)

##############################################################################

"""
Simple sanity checks
"""
print(f"Crawled {len(site_results)}/{len(site_list)} sites.")
count = 0
our_sites = set(list(site_results.keys()) + site_queue)
for site in set(site_list):
    if site not in our_sites:
        count += 1
        print(f"Missing site: '{site}'.")
print(f"{count} missing sites.")

"""
Check which crawled sites were actually successful.
A successful site must have:
1. a successful domain -> url resolution
2. no unexpected crawl exceptions
3. was not terminated via SIGKILL
"""
successful_sites = []
for domain, result in site_results.items():
    result: CrawlResults
    if result.get("url") and not result.get("unexpected_exception") and not result.get("SIGKILL"):
        successful_sites.append(domain)
print(f"{len(successful_sites)} successful sites.")

###########

def screenshot_comparison(sites: list) -> pd.DataFrame:
    results = []
    for i, domain in enumerate(sites):
        print(f"Analyzing site {i+1}/{len(successful_sites)}.")

        clickstreams = get_directories(site_results[domain]["data_path"])
        screenshot_sims = []
        for clickstream in clickstreams:
            for num_action in range(config["CLICKSTREAM_LENGTH"]+1):
                baseline_path = clickstream / f"baseline-{num_action}.png"
                control_path = clickstream / f"control-{num_action}.png"
                experimental_path = clickstream / f"experimental-{num_action}.png"
                
                if os.path.isfile(baseline_path) and os.path.isfile(control_path) and os.path.isfile(experimental_path):
                    CHUNK_SIZE = 40
                    baseline_shingle = ImageShingle(baseline_path, chunk_size = CHUNK_SIZE)
                    control_shingle = ImageShingle(control_path, chunk_size = CHUNK_SIZE)
                    experimental_shingle = ImageShingle(experimental_path, chunk_size = CHUNK_SIZE)

                    try:
                        screenshot_sims.append(ImageShingle.compare_with_control(baseline_shingle, control_shingle, experimental_shingle))
                    except ValueError as e:
                        print(e)

        if len(screenshot_sims) == 0:
            print(f"Skipping {domain} since no comparisons could be made.")
            continue

        screenshot_similarity = statistics.mean(screenshot_sims)
        sceenshot_difference = 1 - screenshot_similarity
        results.append({
            "domain": domain,
            "screenshot_difference": sceenshot_difference,
            f"samples": len(screenshot_sims),
        })

    return pd.DataFrame(results)

screenshots = screenshot_comparison(successful_sites)
screenshots.to_csv(ANALYSIS_PATH / "screenshots.csv", index=False)