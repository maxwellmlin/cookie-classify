#!/usr/bin/env python

from seleniumwire import webdriver
from selenium.webdriver import FirefoxOptions

import utils


class Crawler:
    def __init__(self) -> None:
        options = FirefoxOptions()
        options.add_argument("--headless")  # TODO: get native working

        self.driver = webdriver.Firefox(options=options)

    def get_with_intercept(self, url, interceptor):
        """
        Shihan's algorithm
        """

        domain = utils.get_domain(url)
        data_path = f"./data/{domain}/"

        # Initial crawl to collect all site cookies
        self.driver.get(url)

        # Screenshot with all cookies
        self.driver.refresh()
        self.driver.save_full_page_screenshot(data_path + "all_cookies.png")

        # Screenshot with intercept
        self.driver.request_interceptor = interceptor

        self.driver.refresh()
        self.driver.save_full_page_screenshot(data_path + "remove_necessary.png")
