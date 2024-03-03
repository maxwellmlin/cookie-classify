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
WORKERS = 25
missing_sites = len(site_list) - (WORKERS + len(set(site_queue + list(site_results.keys()))))
if missing_sites > 0:
    print(f"WARNING: {missing_sites} Missing sites!")
else:
    print("All sites accounted for.")

print(f"Crawled {len(site_results)}/{len(site_list)} sites.")

"""
Check which crawled sites were actually successful.
A successful site must have:
1. an available landing page
2. no unexpected crawl exceptions
"""
_keys = set()
successful_sites = []
for domain, result in site_results.items():
    _keys.update(result.keys())
    result: CrawlResults
    if not result.get("unexpected_exception") and not result.get("landing_page_down") and not result.get("SIGKILL"):
        successful_sites.append(domain)
print(f"{len(successful_sites)} successful sites.")
print(_keys)

def screenshot_comparison() -> pd.DataFrame:
    rows_list = []

    for i, domain in enumerate(successful_sites):
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
        stdev = statistics.stdev(screenshot_sims)
        rows_list.append({
            "domain": domain,
            f"screenshot_difference": sceenshot_difference,
            f"stdev": stdev,
            f"samples": len(screenshot_sims),
        })

    return pd.DataFrame(rows_list)

screenshots = screenshot_comparison()
screenshots.to_csv(ANALYSIS_PATH / "screenshots.csv", index=False)