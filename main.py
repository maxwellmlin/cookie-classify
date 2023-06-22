#!/usr/bin/env python

from seleniumwire import webdriver
from selenium.webdriver import FirefoxOptions

from cookie_request_header import CookieRequestHeader

import tldextract

import os


def get_domain(url):
    """
    Return domain of URL.

    `url` is the URL to get the domain from.
    """
    separated_url = tldextract.extract(url)
    return f'{separated_url.domain}.{separated_url.suffix}'


def remove_necessary_interceptor(request):
    """
    Interceptor that removes all necessary cookies from a GET request.

    `request` is the GET request.
    """
    if request.headers.get("Cookie") is None:
        return

    cookie_header = CookieRequestHeader(DOMAIN, request.headers["Cookie"])  # TODO: Is the URL correct?
    cookie_header.remove_necessary()
    modified_header = cookie_header.get_header()

    if modified_header != request.headers["Cookie"]:
        print("Original header: " + request.headers["Cookie"])
        print("Modified header: " + modified_header)
        print()

    request.headers["Cookie"] = modified_header


SITE_URL = "https://bmj.com"
DOMAIN = get_domain(SITE_URL)
SCREENSHOTS_PATH = f"./screenshots/{DOMAIN}/"

if not os.path.exists(SCREENSHOTS_PATH):
    os.mkdir(SCREENSHOTS_PATH)

options = FirefoxOptions()
options.add_argument("--headless")  # TODO: get native working

driver = webdriver.Firefox(options=options)

"""
Initial crawl to collect all site cookies
"""
driver.get(SITE_URL)
driver.save_full_page_screenshot(SCREENSHOTS_PATH + "initial_crawl.png")

"""
Second crawl without necessary cookies
"""

# Set the interceptor on the driver
driver.request_interceptor = remove_necessary_interceptor

driver.get(SITE_URL)
driver.save_full_page_screenshot(SCREENSHOTS_PATH + "remove_necessary_crawl.png")
