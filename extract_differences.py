import os
from typing import Set
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
(ANALYSIS_PATH / "slurm/differences").mkdir(parents=True, exist_ok=True)

# Config
with open(DATA_PATH / "config.yaml", "r") as stream:
    config = yaml.safe_load(stream)

# Site list
site_list = []
with open(config["SITE_LIST_PATH"]) as file:
    for line in file:
        site_list.append(line.strip())

# Site queue
queue_lock = FileLock(config["QUEUE_PATH"] + '.lock', timeout=60)
with queue_lock:
    with open(config["QUEUE_PATH"], 'r') as file:
        site_queue = json.load(file)

# Site results
results_lock = FileLock(config["RESULTS_PATH"] + '.lock', timeout=60)
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
keys: Set[str] = set()
for domain, result in site_results.items():
    keys.update(result.keys())
    if result.get("url") and not result.get("SIGKILL") and not result.get("unexpected_exception"):
        successful_sites.append(domain)
    else:
        unsuccessful_sites.append(domain)
print(f"{len(successful_sites)} successful sites.")

##############################################################################

import logging
from config import LOGGER_NAME

# Set up logging
logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")
log_stream = logging.StreamHandler()
log_stream.setLevel(logging.DEBUG)
log_stream.setFormatter(formatter)
logger.addHandler(log_stream)

array = list(split(successful_sites, 25))
try:
    SLURM_ARRAY_TASK_ID = int(os.getenv('SLURM_ARRAY_TASK_ID')) # type: ignore
except Exception:
    SLURM_ARRAY_TASK_ID = 0

def jaccard_distance(dict1, dict2):
    """
    Computes the Jaccard difference between two frequency dictionaries.
    """
    # Calculate the intersection of keys
    intersection_keys = set(dict1.keys()).intersection(set(dict2.keys()))
    intersection_sum = sum(min(dict1.get(k, 0), dict2.get(k, 0)) for k in intersection_keys)

    # Calculate the union of keys
    union_keys = set(dict1.keys()).union(set(dict2.keys()))
    union_sum = sum(max(dict1.get(k, 0), dict2.get(k, 0)) for k in union_keys)

    # Calculate Jaccard difference
    if union_sum == 0:
        return 0

    sim = intersection_sum / union_sum
    return 1 - sim

def extract_differences(sites: list) -> dict:
    """
    Extract differences for a list of sites.
    
    Return dict schema:
    {
        domain: {
            clickstream: {
                action: [
                    {
                        "bce_diff": float,
                        "shingle_control_diff": float,
                        "shingle_experimental_diff": float,
                        "shingle_did": float
                        "innerText_control_diff": float,
                        "innerText_experimental_diff": float,
                        "innerText_did": float
                        "links_control_diff": float,
                        "links_experimental_diff": float,
                        "links_did": float
                        "img_control_diff": float,
                        "img_experimental_diff": float,
                        "img_did": float
                    }
                ]
            }
        }
    }
    """
    # Initialize results dictionary
    # domain -> clickstream -> action -> feature -> value
    res: dict[str, dict[int, dict[int, dict[str, float]]]] = {}
    for domain in sites:
        res[domain] = {}
        for clickstream in get_directories(site_results[domain]["data_path"]):
            res[domain][int(clickstream.name)] = {}
            for num_action in range(config["CLICKSTREAM_LENGTH"]+1):
                res[domain][int(clickstream.name)][num_action] = {}
    
    for i, domain in enumerate(sites):
        logger.info(f"Analyzing {domain} ({i+1}/{len(sites)}).")

        clickstreams = get_directories(site_results[domain]["data_path"])
        for clickstream in clickstreams:
            # 
            # FEATURE COMPARISON
            #
            
            # Read extracted features from file
            features_path = clickstream / "features.json"
            features = None
            if features_path.is_file():
                with open(features_path) as data:
                    try:
                        features = json.load(data)
                    except json.JSONDecodeError:
                        logger.exception(f"Failed to read {features_path}.")

            """
            Features schema
            
            For a given (domain, clickstream):
            {
                "innerText/links/img": {
                    "baseline/control/experimental": [
                        # Frequency dictionaries for each action
                        {
                            word: count
                        }
                    ]
                }
            }
            """

            # Compute Jaccard difference
            if features:
                for feature in ["innerText", "links", "img"]:
                    # Guard against missing data
                    if features[feature].get("baseline") is None or features[feature].get("control") is None or features[feature].get("experimental") is None:
                        continue
                    for action, (baseline, control, experimental) in enumerate(zip(features[feature]["baseline"], features[feature]["control"], features[feature]["experimental"])):
                        control_diff = jaccard_distance(baseline, control)
                        experimental_diff = jaccard_distance(baseline, experimental)
                        diff_dict = {
                            f"{feature}_control_diff": control_diff,
                            f"{feature}_experimental_diff": experimental_diff,
                            f"{feature}_did": experimental_diff - control_diff
                        }
                        res[domain][int(clickstream.name)][action].update(diff_dict)
                
            #
            # SCREENSHOT COMPARISON
            #
            for num_action in range(config["CLICKSTREAM_LENGTH"]+1):
                baseline_path = clickstream / f"baseline-{num_action}.png"
                control_path = clickstream / f"control-{num_action}.png"
                experimental_path = clickstream / f"experimental-{num_action}.png"
                
                if baseline_path.is_file() and control_path.is_file() and experimental_path.is_file():
                    # Create image shingles
                    CHUNK_SIZE = 40
                    baseline_shingle = ImageShingle(baseline_path, chunk_size = CHUNK_SIZE)
                    control_shingle = ImageShingle(control_path, chunk_size = CHUNK_SIZE)
                    experimental_shingle = ImageShingle(experimental_path, chunk_size = CHUNK_SIZE)

                    diff_dict = {}

                    # Baseline, Control, Experimental (BCE) Difference
                    try:
                        bce_diff = ImageShingle.compare_with_control(baseline_shingle, control_shingle, experimental_shingle)
                        diff_dict["bce_diff"] = bce_diff
                    except ValueError as e:
                        logger.error(f"Failed to compute bce_diff for {domain} ({clickstream.name}, {num_action}). Reason: {e}")
                        
                    # Screenshots Difference in Difference
                    try:
                        control_diff = jaccard_distance(baseline_shingle.shingle_count, control_shingle.shingle_count)
                        experimental_diff = jaccard_distance(baseline_shingle.shingle_count, experimental_shingle.shingle_count)
                        diff_dict["shingle_control_diff"] = control_diff
                        diff_dict["shingle_experimental_diff"] = experimental_diff
                        diff_dict["shingle_did"] = experimental_diff - control_diff
                    except ValueError as e:
                        logger.error(f"Failed to compute shingle_did for {domain} ({clickstream.name}, {num_action}). Reason: {e}")

                    # Update results
                    res[domain][int(clickstream.name)][num_action].update(diff_dict)

    return res

start_time = time.time()
res = extract_differences(array[SLURM_ARRAY_TASK_ID])
# Save the dictionary to a JSON file
with open(ANALYSIS_PATH / f"slurm/differences/{SLURM_ARRAY_TASK_ID}.json", 'w') as f:
    json.dump(res, f)
print(f"Completed in {time.time() - start_time} seconds.")

