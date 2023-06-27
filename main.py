import os
import functools

from crawler import Crawler
import interceptors
import utils

SITE_LIST_PATH = "inputs/sites/sites.txt"  # Path to list of sites to crawl

# Get list of sites to crawl
sites = []
with open(SITE_LIST_PATH) as file:
    for line in file:
        sites.append(line.strip())

for site_url in sites:
    # Create data folder
    data_path = f"./crawls/{utils.get_full_domain(site_url)}/"
    if not os.path.exists(data_path):
        os.mkdir(data_path)

    # Reinstantiate crawler to clear cookies
    crawler = Crawler()

    # Remove necessary cookies
    interceptor = functools.partial(
        interceptors.remove_necessary_interceptor,
        domain=utils.get_domain(site_url),
        data_path=data_path,
    )

    # Shihan's algorithm
    crawler.get_with_intercept(site_url, interceptor, data_path)
