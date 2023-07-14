import functools
from collections import deque
from enum import Enum
from pathlib import Path
from typing import Optional
import os
import time
import shutil
import validators
import json

import bannerclick.bannerdetection as bc

import seleniumwire.request
from seleniumwire import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By

from cookie_database import CookieClass
import interceptors
import utils
from url import URL


class CrawlType(Enum):
    FIRST_RUN = "first_run"  # Gather cookies
    LOG_NORMAL = "normal"  # Screenshot all cookies
    LOG_INTERCEPT = "intercept"  # Screenshot only necessary


class BannerType(Enum):
    ACCEPT_ONLY = 0
    ACCEPT_REJECT = 1
    ACCEPT_SETTINGS = 2


class Data:
    url = ""
    ttw = 0
    sql_addr = None
    status = None
    index = None
    banners = []
    banners_data = []
    CMP = {}
    openwpm = True


class Crawler:
    """Crawl websites, intercept requests, and take screenshots."""

    def __init__(self, data_path: str, save_har: bool = False) -> None:
        """
        Args:
            data_path: Path to store log files and save screenshots.
            save_har: Whether to save HAR data. Defaults to False.
        """
        options = FirefoxOptions()
        options.add_argument("--headless")  # TODO: native does not work

        seleniumwire_options = {}
        if save_har:
            seleniumwire_options['enable_har'] = True

        self.save_har = save_har

        self.driver = webdriver.Firefox(options=options, seleniumwire_options=seleniumwire_options)

        self.time_to_wait = 5  # seconds
        self.total_get_attempts = 3

        self.data_path = data_path

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
        options = FirefoxOptions()
        options.add_argument("--headless")
        temp_driver = webdriver.Firefox(options=options)
        temp_driver.get(url)
        time.sleep(self.time_to_wait)

        domain = utils.get_domain(url)
        url_after_redirect = temp_driver.current_url
        domain_after_redirect = utils.get_domain(url_after_redirect)

        temp_driver.quit()

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
            start_node: URL where traversal will begin. Future crawls will be constrained to this domain.
            crawl_type: Affects intercept and screenshot behavior: TODO: expand
            depth: Number of layers of the DFS. Defaults to 2.
        """

        if depth < 0:
            raise ValueError("Depth must be non-negative.")

        print(f"Starting '{crawl_type.name}'.")

        # Start with the landing page
        urls_to_visit: deque[tuple[URL, int]] = deque([(URL(start_node), 0)])  # (url, depth)
        previous: dict[URL, Optional[str]] = {URL(start_node): None}  # map url to previous url
        redirects: set[URL] = set()  # set of URLs after redirect(s)

        domain = utils.get_domain(start_node)

        # Graph search loop
        while urls_to_visit:
            current_url, current_depth = urls_to_visit.pop()  # DFS

            # Create uid for `current_url` if it does not exist
            if current_url not in self.uids:
                self.uids[current_url] = self.next_uid
                Path(self.data_path + f"{self.next_uid}/").mkdir(parents=True, exist_ok=True)

                self.next_uid += 1

            # Lookup uid
            uid = self.uids[current_url]
            if uid == -1:  # Indicates a duplicate URL that was discovered after redirection
                continue

            uid_data_path = self.data_path + f"{uid}/"

            # Log site visit
            msg = f"Visiting '{current_url.url}' (UID: {uid}) at depth {current_depth}."
            print(msg)
            if not os.path.isfile(self.data_path + f"{uid}/logs.txt"):
                with open(self.data_path + f"{uid}/logs.txt", "a") as file:
                    file.write(msg + "\n\n")

            # Define request interceptor
            def interceptor(request: seleniumwire.request.Request):
                referer_interceptor = functools.partial(
                    interceptors.set_referer_interceptor,
                    url=current_url.url,
                    referer=previous.get(current_url),
                    data_path=uid_data_path
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
                        data_path=uid_data_path
                    )
                    remove_cookie_class_interceptor(request)  # Intercept cookies

            # Set request interceptor
            self.driver.request_interceptor = interceptor

            # Remove previous HAR entries
            del self.driver.requests

            # Visit the current URL with multiple attempts
            attempt = 0
            for attempt in range(self.total_get_attempts):
                try:
                    self.driver.get(current_url.url)
                    break  # If successful, break out of the loop

                except Exception as e:
                    print(f"'{e}' on attempt {attempt+1}/{self.total_get_attempts} for '{current_url.url}'.")
            if attempt == self.total_get_attempts - 1:
                print(f"{self.total_get_attempts} attempts failed for {current_url.url}. Skipping...")
                continue

            # Wait for redirects and dynamic content
            time.sleep(self.time_to_wait)

            # Account for redirects
            after_redirect = URL(self.driver.current_url)
            if after_redirect in redirects:
                print("Redirect to duplicate site. Skipping...")

                shutil.rmtree(uid_data_path)
                self.uids[current_url] = -1  # Mark as duplicate
                continue

            redirects.add(after_redirect)

            # Account for domain name changes
            if after_redirect.domain() != domain:
                print("Redirect to different domain. Skipping...")
                continue

            # Save a screenshot of the viewport  # TODO: save full page screenshot
            if crawl_type in (CrawlType.LOG_NORMAL, CrawlType.LOG_INTERCEPT):
                self.save_viewport_screenshot(uid_data_path + f"{crawl_type.value}.png")

            # Save HAR file
            if self.save_har and crawl_type != CrawlType.FIRST_RUN:
                self.save_har_to_disk(uid_data_path + f"{crawl_type.value}.json")

            # Don't need to visit neighbors if we're at the maximum depth
            if current_depth == depth:
                continue

            # Find all the anchor elements (links) on the page
            a_elements = self.driver.find_elements(By.TAG_NAME, 'a')
            hrefs = [link.get_attribute('href') for link in a_elements]

            # Visit neighbors
            for neighbor in hrefs:
                if neighbor is None or utils.get_domain(neighbor) != domain or not validators.url(neighbor):
                    # NOTE: Potential for false negatives if the href domain
                    # is not the same as the current domain but redirects to the current domain.
                    # However, this is unlikely to occur in practice and
                    # we do not want to visit every href present on the page (`self.time_to_wait` penalty).
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

    def bannerclick(self, domain, url):
        global driver  # :(
        driver = self.driver
        # banners = bc.run_banner_detection(Data)
        # print(banners)
        # Data.banners = banners
        # Data.banners_data = bc.extract_banners_data(banners)
        # bc.interact_with_banners(Data, 1)  # choice 1. accept 2. reject
        # cd.set_webdriver(webdriver)
        # Data.CMP = cd.run_cmp_detection()
        # Data.sql_addr = manager_params.storage_controller_address
        # bc.set_data_in_db_error(Data)

        # TODO: do we need this?
        # bc.halt_for_sleep(Data)
        self.driver.get(url)
        bc.run_all_for_domain(domain, url, self.driver)

    def save_har_to_disk(self, file_path: str) -> None:
        """
        Save current HAR file to `file_path`.

        NOTE: Requests continually get logged to the same HAR file.
        To start logging a new HAR file, use: `del self.driver.requests`.

        Args:
            file_path: Path to save the HAR file. The file extension should be `.json`.
        """
        if not file_path.lower().endswith(".json"):
            raise ValueError("File extension must be `.json`.")

        data = json.loads(self.driver.har)

        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)

    def quit(self) -> None:
        """Safely end the web driver."""
        self.driver.quit()
