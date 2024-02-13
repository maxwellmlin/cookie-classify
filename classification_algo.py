import os
import pandas as pd
import json
import statistics
from pathlib import Path
import yaml
import matplotlib.pyplot as plt
import matplotlib as mpl

from crawler import CrawlResults

from utils.utils import get_directories, get_domain
from utils.image_shingle import ImageShingle

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

##############################################################################

CRAWL_NAME = '3N76L-top-250'
DATA_PATH = Path("/usr/project/xtmp/mml66/cookie-classify/") / CRAWL_NAME
ANALYSIS_PATH = Path("analysis") / CRAWL_NAME
ANALYSIS_PATH.mkdir(parents=True, exist_ok=True)

##############################################################################

"""
Load meta.yaml
"""

with open(DATA_PATH / "meta.yaml", "r") as stream:
    meta = yaml.safe_load(stream)

CRAWL_NAME = meta['CRAWL_NAME']
SITE_LIST_PATH = meta['SITE_LIST_PATH']
TOTAL_ACTIONS = meta['TOTAL_ACTIONS']
CLICKSTREAM_LENGTH = meta['CLICKSTREAM_LENGTH']

print(meta)

"""
CDN Domains
"""
cdn_domains = set()
with open("inputs/cdn/cnamechain.json") as file:
    data = json.load(file)
    for cdn in data:
        cdn_domains.add(get_domain(cdn[0]))

"""
Run Statistics
"""
# Sites that we wanted to crawl
sites_to_crawl = []
with open (DATA_PATH / SITE_LIST_PATH) as file:
    for line in file:
        sites_to_crawl.append(line.strip())

# Sites that we actually crawled
with open(DATA_PATH / "sites.json") as file:
    site_results: dict[str, CrawlResults] = json.load(file)

# Check whether we actually crawled all of the sites in our original site list. If not, it is likely that one of the workers hanged or was killed.
print(f"Crawled {len(site_results)}/{len(sites_to_crawl)} sites.")

"""
Check which crawled sites were actually successful.
A successful site must have:
1. an available landing page
2. no unexpected crawl exceptions
"""
successful_sites = []
for domain, result in site_results.items():
    result: CrawlResults
    if result["unexpected_exception"] is False and result["landing_page_down"] is False:
        successful_sites.append(domain)
print(f"Successfully crawled {len(successful_sites)}/{len(site_results)} sites.")

###

def screenshot_comparison() -> pd.DataFrame:
    rows_list = []

    for i, domain in enumerate(successful_sites):
        print(f"Analyzing site {i+1}/{len(successful_sites)}.")

        clickstreams = get_directories(site_results[domain]["data_path"])
        screenshot_sims = []
        for clickstream in clickstreams:
            for num_action in range(CLICKSTREAM_LENGTH+1):
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