#!/usr/bin/env python

import functools
from collections import deque
from enum import Enum
from pathlib import Path
from typing import Optional
import os

import seleniumwire.request
from seleniumwire import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import interceptors
import utils
from url import URL


class CrawlType(Enum):
    FIRST_RUN = 0  # Initial run
    LOG_NORMAL = 1  # Screenshot all cookies
    LOG_INTERCEPT = 2  # Screenshot only necessary


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
        self.data_path = data_path

        self.uids: dict[URL, int] = {}  # map url to a unique id
        self.next_uid = 1

    def crawl(self, url: str) -> None:
        """
        Crawl website.

        Get a website and click the accept button to obtain all cookies.
        Then, refresh to load the website with all cookies.
        Finally, refresh with an interceptor to remove cookies.

        Args:
            url: URL of the website to crawl.
        """

        # Check if `url` results in redirects
        domain = utils.get_domain(url)
        self.driver.get(url)
        url_after_redirect = self.driver.current_url
        domain_after_redirect = utils.get_domain(url_after_redirect)

        if domain_after_redirect != domain:
            with open(self.data_path + "logs.txt", "a") as file:
                file.write(f"WARNING: Domain name changed from '{domain}' to '{domain_after_redirect}'.\n")
        if url_after_redirect != url:
            with open(self.data_path + "logs.txt", "a") as file:
                file.write(f"WARNING: URL changed from '{url}' to '{url_after_redirect}'.\n")

        # Initial crawl to collect all site cookies
        self.crawl_inner_pages(url_after_redirect, CrawlType.FIRST_RUN)

        # Screenshot with all cookies
        self.crawl_inner_pages(url_after_redirect, CrawlType.LOG_NORMAL)

        # Screenshot with intercept
        self.crawl_inner_pages(url_after_redirect, CrawlType.LOG_INTERCEPT)

    def crawl_inner_pages(self, start_node: str, crawl_type: CrawlType, depth: int = 2):
        """
        Crawl inner pages of website with a given depth.

        Screenshot folder structure: domain/uid/name.png
        where each url has a unique uid and name is either:
        "all_cookies" or "intercept".
        The domain is the domain of the url (before any redirect)
        to ensure consistency with the site list.

        Args:
            start_node: URL where traversal will begin.
            crawl_type: Affects intercept and screenshot behavior: TODO: expand
            depth: Number of layers of the DFS. Defaults to 1.
        """

        domain = utils.get_domain(start_node)

        # Start with the landing page
        urls_to_visit: deque[tuple[URL, int]] = deque()
        urls_to_visit.append((URL(start_node), 0))
        previous: dict[URL, Optional[str]] = {URL(start_node): None}  # map url to previous url
        while urls_to_visit:
            current_url, current_depth = urls_to_visit.pop()  # DFS
            self.driver.get(current_url.url)
            current_url = URL(self.driver.current_url)  # get the actual url after redirects

            # Terminate if the maximum depth has been reached or if the domain has changed
            if current_depth > depth or utils.get_domain(current_url.url) != domain:
                continue

            if current_url in self.uids:
                uid = self.uids[current_url]
            else:
                uid = self.next_uid
                self.next_uid += 1
                self.uids[current_url] = uid
                Path(self.data_path + f"{uid}/").mkdir(parents=True, exist_ok=True)

            msg = f"Visiting {current_url.url} (UID: {uid}) at depth {current_depth}."
            print(msg)
            if not os.path.isfile(self.data_path + f"{uid}/logs.txt"):
                with open(self.data_path + f"{uid}/logs.txt", "a") as file:
                    file.write(msg + "\n\n")

            if crawl_type == CrawlType.LOG_INTERCEPT:
                # Intercept cookie header and set the referer
                remove_necessary_interceptor = functools.partial(
                    interceptors.remove_necessary_interceptor,
                    domain=domain,
                    data_path=self.data_path + f"{uid}/",
                )
                referer_interceptor = functools.partial(
                    interceptors.set_referer_interceptor,
                    referer=previous.get(current_url),
                    data_path=self.data_path + f"{uid}/"
                )

                def interceptor(request: seleniumwire.request.Request):
                    remove_necessary_interceptor(request)
                    referer_interceptor(request)

            else:
                # Just set the referer
                interceptor = functools.partial(
                    interceptors.set_referer_interceptor,
                    referer=previous.get(current_url),
                    data_path=self.data_path + f"{uid}/"
                )
            self.driver.request_interceptor = interceptor

            # Visit the current URL
            self.driver.get(current_url.url)

            # Save a screenshot of the viewport
            if crawl_type in (CrawlType.LOG_NORMAL, CrawlType.LOG_INTERCEPT):
                self.save_viewport_screenshot(self.data_path + f"{uid}/{crawl_type}.png")

            # Find all the anchor elements (links) on the page
            a_elements = self.driver.find_elements(By.TAG_NAME, 'a')
            hrefs = [link.get_attribute('href') for link in a_elements if link.get_attribute('href')]

            # Visit neighbors
            for href in hrefs:
                if href is None:
                    continue

                self.driver.get(href)
                href_after_redirect = URL(self.driver.current_url)

                if href_after_redirect not in previous:
                    previous[href_after_redirect] = current_url.url
                    urls_to_visit.append((href_after_redirect, current_depth + 1))

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
