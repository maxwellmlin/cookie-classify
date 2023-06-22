#!/usr/bin/env python

from seleniumwire import webdriver
from selenium.webdriver import FirefoxOptions

SITE_URL = "https://www.google.com"

options = FirefoxOptions()
options.add_argument("--headless")  # TODO: get native working

driver = webdriver.Firefox(options=options)


def interceptor(request):
    """
    Request interceptor
    """
    del request.headers['Referer']  # Delete the header first
    request.headers['Referer'] = 'some_referer'


# Set the interceptor on the driver
driver.request_interceptor = interceptor

"""
Crawl
"""
driver.get(SITE_URL)
