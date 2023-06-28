#!/usr/bin/env python

import functools
import time
from collections import deque

from seleniumwire import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

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

    def crawl(self, url: str) -> None:
        """
        Crawl website.

        Get a website and click the accept button to obtain all cookies.
        Then, refresh to load the website with all cookies.
        Finally, refresh with an interceptor to remove cookies.

        Args:
            url (str): URL of the website to crawl.
        """

        # Initial crawl to collect all site cookies
        self.crawl_inner_pages(url)

        # Screenshot with all cookies
        self.crawl_inner_pages(url, take_screenshots=True)

        # Screenshot with intercept
        interceptor = functools.partial(
            interceptors.remove_necessary_interceptor,
            domain=utils.get_domain(url),
            data_path=self.data_path,
        )
        self.driver.request_interceptor = interceptor
        self.crawl_inner_pages(url, take_screenshots=True)

    def crawl_inner_pages(url: str, depth: int = 2, take_screenshots: bool = False):
        """
        Crawl inner pages of website with a given depth.

        TODO: _extended_summary_

        Args:
            url (str): URL where traversal will begin.
            depth (int, optional): Number of layers of the DFS. Defaults to 2.
            take_screenshots (bool, optional): Defaults to False.
        """

        to_visit_queue = deque()
        to_visit_queue.append(url)
        visited = set()

        # DFS traversal
        while to_visit_queue:
            current_node = to_visit_queue.pop()

            for neighbor in graph[current_node]:
                if neighbor not in visited:
                    visited.add(current_node)
                    to_visit_queue.append(neighbor)
        

    def save_viewport_screenshot(self, file_path: str):
        """
        Save a screenshot of the viewport to a file.

        Args:
            file_path (str): Path to save the screenshot.
        """
        # Take a screenshot of the viewport
        screenshot = self.driver.get_screenshot_as_png()

        # Save the screenshot to a file
        with open(file_path, "wb") as file:
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
