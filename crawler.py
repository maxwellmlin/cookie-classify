#!/usr/bin/env python

import functools
import time

from seleniumwire import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from image_shingles import ImageShingle
import interceptors
import utils


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
        self.time_to_wait = 5  # seconds
        self.data_path = data_path

    def get_with_intercept(self, url: str) -> None:
        """
        Shihan's algorithm.

        Get a website and click the accept button to obtain all cookies.
        Then, refresh to load the website with all cookies.
        Finally, refresh with an interceptor to remove cookies.

        Args:
            url (str): URL of the website to crawl.
        """

        all_data_path = self.data_path + "all_cookies.png"
        intercept_data_path = self.data_path + "intercept.png"

        # Initial crawl to collect all site cookies
        self.driver.get(url)
        time.sleep(self.time_to_wait)
        # self.click_accept()  # Get all JavaScript cookies

        # Screenshot with all cookies
        self.driver.refresh()
        time.sleep(self.time_to_wait)
        self.save_viewport_screenshot(all_data_path)

        # Screenshot with intercept
        interceptor = functools.partial(
            interceptors.remove_necessary_interceptor,
            domain=utils.get_domain(url),
            data_path=self.data_path,
        )
        self.driver.request_interceptor = interceptor
        self.driver.refresh()
        time.sleep(self.time_to_wait)
        self.save_viewport_screenshot(intercept_data_path)

        # Compare screenshots using image shingles
        shingle_size = 40
        all_shingles = ImageShingle(all_data_path, shingle_size)
        intercept_shingles = ImageShingle(intercept_data_path, shingle_size)

        similarity = all_shingles.compare(intercept_shingles)
        with open(self.data_path + "logs.txt", "a") as file:
            file.write(f"Similarity: {similarity}")

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
        """
        Click the OneTrust accept button to accept all JavaScript cookies.

        BUG: The driver does not always find the accept button.
        """
        accept_ID = "onetrust-accept-btn-handler"
        wait_time = 10  # seconds

        try:
            element = WebDriverWait(self.driver, wait_time).until(EC.presence_of_element_located((By.ID, accept_ID)))
            element.click()

            success = True
        except TimeoutException:
            success = False

        msg = "Accept button clicked" if success else f"Accept button not found after {wait_time} seconds"
        with open(self.data_path + "logs.txt", "a") as file:
            file.write(f"{msg}\n\n")

    def quit(self) -> None:
        """Safely end the web driver."""
        self.driver.quit()
