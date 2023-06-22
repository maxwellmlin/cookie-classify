#!/usr/bin/env python

from seleniumwire import webdriver
from selenium.webdriver import FirefoxOptions

from cookie_request_header import CookieRequestHeader

SITE_URL = "https://screenconnect.com"
SCREENSHOTS_PATH = "./screenshots/"

options = FirefoxOptions()
options.add_argument("--headless")  # TODO: get native working

driver = webdriver.Firefox(options=options)


def remove_necessary_interceptor(request):
    """
    Interceptor that removes all necessary cookies from a GET request.

    `request` is the GET request.
    """
    if request.headers.get("Cookie") is None:
        return

    cookie_header = CookieRequestHeader(request.url, request.headers["Cookie"])  # TODO: Is the URL correct?
    cookie_header.remove_necessary()
    modified_header = cookie_header.get_header()

    request.headers["Cookie"] = modified_header


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
