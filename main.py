#!/usr/bin/env python

from seleniumwire import webdriver
from selenium.webdriver import FirefoxOptions

from cookie_request_header import CookieRequestHeader

SITE_URL = "https://screenconnect.com"
SCREENSHOTS_PATH = "./screenshots/"

options = FirefoxOptions()
options.add_argument("--headless")  # TODO: get native working

driver = webdriver.Firefox(options=options)
cookie_header = CookieRequestHeader()


def remove_necessary_interceptor(request):
    """
    Interceptor that removes all necessary cookies from the GET request.
    """
    cookie_header.load_header(request.headers["Cookie"], request.url)
    cookie_header.remove_necessary()

    modified_header = cookie_header.get_header()

    request.headers["Cookie"] = modified_header


"""
Initial crawl obtains cookies
"""
driver.get(SITE_URL)
driver.save_full_page_screenshot(SCREENSHOTS_PATH + "initial_crawl.png")

"""
Second crawl removes all necessary cookies
"""

# Set the interceptor on the driver
driver.request_interceptor = remove_necessary_interceptor

driver.get(SITE_URL)
driver.save_full_page_screenshot(SCREENSHOTS_PATH + "second_crawl.png")
