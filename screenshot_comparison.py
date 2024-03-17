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
from utils.utils import get_directories, get_domain, split
from utils.image_shingle import ImageShingle
import time
import numpy as np

CRAWL_NAME = 'KJ2GW'

DATA_PATH = Path("/usr/project/xtmp/mml66/cookie-classify/") / CRAWL_NAME
ANALYSIS_PATH = Path("analysis") / CRAWL_NAME
for name in ["innerText", "links", "img", "screenshots"]:
    (ANALYSIS_PATH / "slurm" / name).mkdir(parents=True, exist_ok=True)

# Config
with open(DATA_PATH / "config.yaml", "r") as stream:
    config = yaml.safe_load(stream)

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

"""
Check crawl completion.
"""
print(f"Crawled {len(site_results)}/{len(site_list)} sites.")

"""
Reduce the number of sites to analyze.
A successful site must have:
1. a successful domain -> url resolution
3. was not terminated via SIGKILL
2. no unexpected crawl exceptions
"""
successful_sites = []
unsuccessful_sites = []
keys = set()
for domain, result in site_results.items():
    result: CrawlResults
    keys.update(result.keys())
    if result.get("url") and not result.get("SIGKILL") and not result.get("unexpected_exception"):
        successful_sites.append(domain)
    else:
        unsuccessful_sites.append(domain)
print(f"{len(successful_sites)} successful sites.")
print(keys)

##############################################################################

array = list(split(successful_sites, 25))
try:
    SLURM_ARRAY_TASK_ID = int(os.getenv('SLURM_ARRAY_TASK_ID')) # type: ignore
except Exception:
    SLURM_ARRAY_TASK_ID = 0

def screenshot_comparison(sites: list) -> pd.DataFrame:
    """
    Compare screenshots of sites using baseline, control, and experimental images.
    """
    results = {}
    for i, domain in enumerate(sites):
        results[domain] = {}
        
        print(f"Analyzing site {i+1}/{len(sites)}.")

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

                    # Baseline, Control, Experimental (BCE) Difference
                    try:
                        bce_diff = ImageShingle.compare_with_control(baseline_shingle, control_shingle, experimental_shingle)
                        results[domain][num_action]["bce_diff"] = bce_diff
                    except ValueError as e:
                        print(e)
                        
                    # Baseline/Control - Baseline/Experimental Difference in Difference
                    try:
                        control_diff = baseline_shingle.compute_difference(control_shingle)
                        experimental_diff = baseline_shingle.compute_difference(experimental_diff)

                        results[domain][num_action]["control_diff"] = control_diff
                        results[domain][num_action]["experimental_diff"] = experimental_diff
                        results[domain][num_action]["diff_in_diff"] = experimental_diff - control_diff
                        
                    except ValueError as e:
                        print(e)

    return results

start_time = time.time()
screenshots = screenshot_comparison(array[SLURM_ARRAY_TASK_ID])
# Save the dictionary to a JSON file
with open(ANALYSIS_PATH / f"slurm/screenshots/{SLURM_ARRAY_TASK_ID}.json", 'w') as f:
    json.dump(screenshots, f)
print(f"Completed in {time.time() - start_time} seconds.")

