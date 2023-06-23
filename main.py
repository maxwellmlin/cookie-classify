from crawler import Crawler
import interceptors
import functools
import utils
import os

SITE_LIST_PATH = "inputs/sites/20sites.txt"

sites = []
with open(SITE_LIST_PATH) as file:
    for line in file:
        sites.append(line.strip())

for site_url in sites:
    crawler = Crawler()  # Reinstantiate crawler to clear cookies

    # Remove necessary cookies
    interceptor = functools.partial(
        interceptors.remove_necessary_interceptor,
        domain=utils.get_domain(site_url),
        logging=True
    )

    # Create data folder
    data_path = f"./data/{utils.get_domain(site_url)}/"
    if not os.path.exists(data_path):
        os.mkdir(data_path)

    # Remove all cookies
    # interceptor = interceptors.remove_all_interceptor

    # No inteceptor
    # interceptor = interceptors.passthrough_interceptor

    # Shihan's algorithm
    crawler.get_with_intercept(site_url, interceptor)
