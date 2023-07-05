import functools
from collections import deque
from enum import Enum
from pathlib import Path
from typing import Optional
import os
import time
import requests
import shutil

import seleniumwire.request
from seleniumwire import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from cookie_database import CookieClass
import interceptors
import utils
from url import URL


class CrawlType(Enum):
    FIRST_RUN = "first_run"  # Gather cookies
    LOG_NORMAL = "normal"  # Screenshot all cookies
    LOG_INTERCEPT = "intercept"  # Screenshot only necessary


class Crawler:
    """Crawl websites, intercept requests, and take screenshots."""

    def __init__(self, data_path: str) -> None:
        """
        Args:
            data_path: Path to store log files and save screenshots.
        """
        options = FirefoxOptions()
        options.add_argument("--headless")  # NOTE: native does not work

        self.driver = webdriver.Firefox(options=options)
        self.time_to_wait = 5  # seconds
        self.total_get_attempts = 3
        self.data_path = data_path

        self.headers = {
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/114.0'
        }

        self.uids: dict[URL, int] = {}  # map url to a unique id
        self.next_uid = 0

    def crawl(self, url: str, depth: int = 2) -> None:
        """
        Crawl website.

        Get a website and click the accept button to obtain all cookies.
        Then, refresh to load the website with all cookies.
        Finally, refresh with an interceptor to remove cookies.

        Args:
            url: URL of the website to crawl.
            depth: Number of layers of the DFS. Defaults to 2.
        """

        # Check if `url` results in redirects
        # NOTE: Does not handle JavaScript redirects
        domain = utils.get_domain(url)
        response = requests.get(url, headers=self.headers)
        url_after_redirect = response.url
        domain_after_redirect = utils.get_domain(url_after_redirect)

        if domain_after_redirect != domain:
            with open(self.data_path + "logs.txt", "a") as file:
                file.write(f"WARNING: Domain name changed from '{domain}' to '{domain_after_redirect}'.\n")
        if url_after_redirect != url:
            with open(self.data_path + "logs.txt", "a") as file:
                file.write(f"WARNING: URL changed from '{url}' to '{url_after_redirect}'.\n")

        # Initial crawl to collect all site cookies
        self.crawl_inner_pages(url_after_redirect, CrawlType.FIRST_RUN, depth)

        # Screenshot with all cookies
        self.crawl_inner_pages(url_after_redirect, CrawlType.LOG_NORMAL, depth)

        # Screenshot with intercept
        self.crawl_inner_pages(url_after_redirect, CrawlType.LOG_INTERCEPT, depth)

    def crawl_inner_pages(self, start_node: str, crawl_type: CrawlType, depth: int = 2):
        """
        Crawl inner pages of website with a given depth.

        Screenshot folder structure: domain/uid/name.png
        The domain is the domain of the url (before any redirect)
        to ensure consistency with the site list.

        Args:
            start_node: URL where traversal will begin.
            crawl_type: Affects intercept and screenshot behavior: TODO: expand
            depth: Number of layers of the DFS. Defaults to 2.
        """

        if depth < 0:
            raise ValueError("Depth must be non-negative.")

        print(f"Starting '{crawl_type.name}'.")

        # Start with the landing page
        urls_to_visit: deque[tuple[URL, int]] = deque([(URL(start_node), 0)])
        previous: dict[URL, Optional[str]] = {URL(start_node): None}  # map url to previous url
        redirects: set[URL] = set()  # set of URLs after redirect(s)

        domain = utils.get_domain(start_node)

        while urls_to_visit:
            current_url, current_depth = urls_to_visit.pop()  # DFS

            # Lookup uid for current url
            if current_url in self.uids:
                uid = self.uids[current_url]
                if uid == -1:
                    # Skip this url
                    # '-1' indicates a duplicate that was discovered after redirect(s)
                    continue
            else:
                uid = self.next_uid
                self.next_uid += 1
                self.uids[current_url] = uid
                Path(self.data_path + f"{uid}/").mkdir(parents=True, exist_ok=True)

            # Log site visit
            msg = f"Visiting '{current_url.url}' (UID: {uid}) at depth {current_depth}."
            print(msg)
            if not os.path.isfile(self.data_path + f"{uid}/logs.txt"):
                with open(self.data_path + f"{uid}/logs.txt", "a") as file:
                    file.write(msg + "\n\n")

            # Set request interceptor
            def interceptor(request: seleniumwire.request.Request):
                referer_interceptor = functools.partial(
                    interceptors.set_referer_interceptor,
                    url=current_url.url,
                    referer=previous.get(current_url),
                    data_path=self.data_path + f"{uid}/"
                )
                referer_interceptor(request)  # Intercept referer to previous page

                if crawl_type == CrawlType.LOG_INTERCEPT:
                    blacklist = tuple([
                        CookieClass.STRICTLY_NECESSARY,
                        # CookieClass.PERFORMANCE,
                        # CookieClass.FUNCTIONALITY,
                        # CookieClass.TARGETING,
                        # CookieClass.UNCLASSIFIED
                    ])

                    remove_cookie_class_interceptor = functools.partial(
                        interceptors.remove_cookie_class_interceptor,
                        blacklist=blacklist,
                        data_path=self.data_path + f"{uid}/",
                    )
                    remove_cookie_class_interceptor(request)  # Intercept cookies

            self.driver.request_interceptor = interceptor

            # Visit the current URL with multiple attempts
            attempt = 0
            for attempt in range(self.total_get_attempts):
                try:
                    self.driver.get(current_url.url)
                    break  # If successful, break out of the loop

                except TimeoutException:
                    print(f"TimeoutException on attempt {attempt}/{self.total_get_attempts}: {current_url.url}.")
            if attempt == self.total_get_attempts - 1:
                print(f"{self.total_get_attempts} attempts failed for {current_url.url}. Skipping...")
                continue

            time.sleep(self.time_to_wait)

            # Account for redirects
            after_redirect = URL(self.driver.current_url)
            if after_redirect in redirects:
                print("Already visited. Skipping...")

                shutil.rmtree(self.data_path + f"{uid}/")
                self.uids[current_url] = -1  # Mark as duplicate
                continue

            redirects.add(after_redirect)

            # Save a screenshot of the viewport  # TODO: save full page screenshot
            if crawl_type in (CrawlType.LOG_NORMAL, CrawlType.LOG_INTERCEPT):
                self.save_viewport_screenshot(self.data_path + f"{uid}/{crawl_type.value}.png")

            # Don't need to visit neighbors if we're at the maximum depth
            if current_depth == depth:
                continue

            # Find all the anchor elements (links) on the page
            a_elements = self.driver.find_elements(By.TAG_NAME, 'a')
            hrefs = [link.get_attribute('href') for link in a_elements]

            # Visit neighbors
            for neighbor in hrefs:
                if neighbor is None or utils.get_domain(neighbor) != domain:
                    continue

                neighbor = URL(neighbor)

                if neighbor not in previous:
                    previous[neighbor] = current_url.url
                    urls_to_visit.append((neighbor, current_depth + 1))

    def save_viewport_screenshot(self, file_path: str):
        """
        Save a screenshot of the viewport to a file.

        Args:
            file_path: Path to save the screenshot.
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
