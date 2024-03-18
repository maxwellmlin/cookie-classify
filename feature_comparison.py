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

def compare_features(sites, feature: str, comparison: tuple[str, str]) -> pd.DataFrame:
    """
    Compute difference in difference of features.
    """
    rows_list = []

    for i, domain in enumerate(sites):
        print(f"Analyzing site {i+1}/{len(sites)}.")
        clickstreams = get_directories(site_results[domain]["data_path"])

        all_action_sims = []
        for clickstream in clickstreams:
            data_path = clickstream / "features.json"
            
            # Skip if the file is missing
            if not data_path.is_file():
                continue
            
            with open(data_path) as features:
                try:
                    features = json.load(features)
                except Exception:
                    continue
                
            # Skip if any of the data is missing
            if features[feature].get("baseline") is None or features[feature].get("control") is None or features[feature].get("experimental") is None:
                continue

            all_action_sims.extend(compare(features[feature][comparison[0]], features[feature][comparison[1]]))

        if len(all_action_sims) == 0:
            print(f"Skipping {domain} since no comparisons could be made.")
            continue

        sim = statistics.mean(all_action_sims)
        diff = 1 - sim

        rows_list.append({
            "domain": domain,
            f"{comparison[1]}_diff": diff,
        })

    return pd.DataFrame(rows_list)

def merge_experiments(sites, feature: str):
    control = compare_features(sites, feature, ("baseline", "control"))
    experimental = compare_features(sites, feature, ("baseline", "experimental"))
    df = pd.merge(control, experimental, on="domain")
    df["diff_in_diff"] = df["experimental_diff"] - df["control_diff"]
    return df

start_time = time.time()
for feature in ["innerText", "links", "img"]:
    df = merge_experiments(array[SLURM_ARRAY_TASK_ID], feature)
    df.to_csv(ANALYSIS_PATH / f"slurm/{feature}/{SLURM_ARRAY_TASK_ID}.csv", index=False)
print(f"Completed in {time.time() - start_time} seconds.")