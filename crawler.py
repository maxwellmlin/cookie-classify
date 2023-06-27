#!/usr/bin/env python

from seleniumwire import webdriver
import seleniumwire.request
from selenium.webdriver import FirefoxOptions
from selenium.common.exceptions import NoSuchElementException
from typing import Callable
import time

from image_shingles import ImageShingles


class Crawler:
    """Crawl websites, intercept requests, and take screenshots."""

    def __init__(self, data_path: str) -> None:
        """
        Args:
            data_path (str): Path to store log files and save screenshots.
        """        
        options = FirefoxOptions()
        options.add_argument("--headless")  # NOTE: native does not work

        self.driver = webdriver.Firefox(options=options)
        self.time_to_wait = 0  # seconds
        self.data_path = data_path

    def get_with_intercept(self,
                           url: str,
                           interceptor: Callable[[seleniumwire.request.Request], None]) -> None:
        """
        Shihan's algorithm.

        Get a website and click the accept button to obtain all cookies.
        Then, refresh to load the website with all cookies.
        Finally, refresh with an interceptor to remove cookies.

        Args:
            url (str): URL of the website to crawl.
            interceptor (Callable[[seleniumwire.request.Request], None]): Function that intercept requests.
        """

        all_data_path = self.data_path + "all_cookies.png"
        intercept_data_path = self.data_path + "intercept.png"

        # Initial crawl to collect all site cookies
        self.driver.get(url)
        self.click_accept()  # Get all JavaScript cookies
        time.sleep(self.time_to_wait)

        # Screenshot with all cookies
        self.driver.refresh()
        time.sleep(self.time_to_wait)
        self.save_viewport_screenshot(all_data_path)

        # Screenshot with intercept
        self.driver.request_interceptor = interceptor
        self.driver.refresh()
        time.sleep(self.time_to_wait)
        self.save_viewport_screenshot(intercept_data_path)

        # Compare screenshots using image shingles
        shingle_size = 40
        all_shingles = ImageShingles(all_data_path, shingle_size)
        intercept_shingles = ImageShingles(intercept_data_path, shingle_size)

        similarity = all_shingles.compare(intercept_shingles)
        with open(self.data_path + "logs.txt", "a") as file:
            file.write(f"Similarity: {similarity}\n")

    def save_viewport_screenshot(self, file_path: str):
        """
        Save a screenshot of the viewport to a file.

        Args:
            file_path (str): Path to save the screenshot.
        """
        # Take a screenshot of the viewport
        screenshot = self.driver.get_screenshot_as_png()

        # Save the screenshot to a file
        with open(file_path, 'wb') as file:
            file.write(screenshot)

    def click_accept(self) -> None:
        """Click the OneTrust accept button to accept all JavaScript cookies."""

        try:
            accept_button = self.driver.find_element_by_id("onetrust-accept-btn-handler")
            accept_button.click()
            success = True
        except NoSuchElementException:
            success = False

        msg = "OneTrust accept button clicked" if success else "OneTrust accept button not found"
        with open(self.data_path + "logs.txt", "a") as file:
            file.write(f"{msg}\n")

    def dispose(self) -> None:
        """Safely ends the web driver."""
        self.driver.Dispose()
