import functools
from collections import deque
from enum import Enum
from pathlib import Path
from typing import Optional, TypedDict
import os
import time
import shutil
import validators
import json
import logging

import bannerclick.bannerdetection as bc

import seleniumwire.request
from seleniumwire import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import JavascriptException, TimeoutException

from cookie_database import CookieClass
import interceptors
import utils
from url import URL
import config


class BannerClickInteractionType(Enum):
    """
    Type of interaction with Accept/Reject cookie notice.

    Enum values correspond to BannerClick's `CHOICE` variable.
    """

    ACCEPT = 1
    REJECT = 2


class CMPType(str, Enum):
    """
    Type of CMP API.

    Enum values correspond to the name of the exposed CMP JavaScript API object.
    """

    NONE = "NONE"  # No CMP found

    ONETRUST = "OneTrust"
    TCF = "__tcfapi"


class CrawlData(TypedDict):
    """
    Class for storing data about a crawl.
    """

    data_path: str
    cmp_names: list[CMPType]  # Empty if no CMP found
    click_success: Optional[bool]  # None if no click was attempted
    down: bool  # True if landing page is inaccessible, False otherwise


class Crawler:
    """
    Crawl websites, intercept requests, and take screenshots.
    """

    logger = logging.getLogger(config.LOGGER_NAME)

    def __init__(self, data_path: str, time_to_wait: int = 5, total_get_attempts: int = 3, page_load_timeout: int = 30, headless: bool = True) -> None:
        """
        Args:
            data_path: Path to store log files and save screenshots.
            time_to_wait: Time to wait between driver get requests. Defaults to 5 seconds.
            total_get_attempts: Number of attempts to get a website. Defaults to 3.
            page_load_timeout: Time to wait for a page to load. Defaults to 30 seconds.
            headless: Whether to run the web driver in headless mode. Defaults to True.
        """
        self.headless = headless
        self.page_load_timeout = page_load_timeout
        self.driver = self.get_driver()

        self.time_to_wait = time_to_wait
        self.total_get_attempts = total_get_attempts

        self.data_path = data_path
        if not os.path.exists(data_path):
            os.mkdir(data_path)

        self.uids: dict[URL, int] = {}  # map url to a unique id
        self.next_uid = 0

    def get_driver(self) -> webdriver.Firefox:
        """
        Initialize and return a Firefox web driver using arguments from `self`.
        """
        options = FirefoxOptions()

        # See: https://stackoverflow.com/a/64724390/21055641
        options.add_argument("start-maximized")
        options.add_argument("disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument('--disable-application-cache')
        options.add_argument('--disable-gpu')

        if self.headless:
            options.add_argument("--headless")

        seleniumwire_options = {
            'enable_har': True,
        }

        driver = webdriver.Firefox(options=options, seleniumwire_options=seleniumwire_options)
        driver.set_page_load_timeout(self.page_load_timeout)

        return driver

    def crawl(self, url: str, depth: int = 0) -> CrawlData:
        """
        Crawl website with repeated calls to `crawl_inner_pages`.

        Args:
            url: URL of the website to crawl.
            depth: Number of layers of the DFS. Defaults to 0.
        """
        data: CrawlData = {"data_path": self.data_path,
                           "cmp_names": [],
                           "click_success": None,
                           "down": False
                           }

        # CMP Detection Only
        # self.crawl_inner_pages(
        #     url,
        #     data=data,
        # )
        # return data

        # Check cookie notice type
        self.crawl_inner_pages(
            url,
            interaction_type=BannerClickInteractionType.REJECT,
            data=data,
        )

        #
        # Website Cookie Compliance Algorithm
        #
        if CMPType.ONETRUST in data["cmp_names"]:
            self.cleanup_driver()
            self.driver = self.get_driver()

            #
            # OneTrust Compliance
            #

            self.crawl_inner_pages(
                url,
                interaction_type=CMPType.ONETRUST,
                data=data
            )

            # TODO: Exit early if injection failed

            self.crawl_inner_pages(
                url,
                crawl_name="onetrust_reject_tracking",
                depth=depth,
            )

            return data

        elif data["click_success"]:
            self.cleanup_driver()
            self.driver = self.get_driver()  # Reset driver

            #
            # Accept/Reject Cookie Notices
            #

            # Collect cookies
            self.crawl_inner_pages(
                url,
                depth=depth
            )

            # Log
            self.crawl_inner_pages(
                url,
                crawl_name="normal",
                depth=depth,
            )

            # Click reject
            self.crawl_inner_pages(
                url,
                interaction_type=BannerClickInteractionType.REJECT,
                data=data
            )
            if not data["click_success"]:
                return data

            # Log
            self.crawl_inner_pages(
                url,
                crawl_name="after_reject",
                depth=depth,
            )

            return data
        else:
            return data

    def crawl_inner_pages(
            self,
            start_node: str,
            crawl_name: str = "",
            depth: int = 0,
            interaction_type: BannerClickInteractionType | CMPType | None = None,
            cookie_blacklist: tuple[CookieClass, ...] = (),
            data: Optional[CrawlData] = None):
        """
        Crawl inner pages of website with a given depth.

        Screenshot folder structure: domain/uid/crawl_name.png
        The domain is the domain of the url (before any redirect)
        to ensure consistency with the site list.

        Args:
            start_node: URL where traversal will begin. Future crawls will be constrained to this domain.
            crawl_name: Name of the crawl, used for file names. Defaults to "", where no files are created.
            depth: Number of layers of the DFS. Defaults to 0.
            interaction_type: Type of interaction with cookie notice/API. Defaults to None, where no action is taken.
            cookie_blacklist: A tuple of cookie classes to remove. Defaults to (), where no cookies are removed.
            data: Object to save global crawl data. Defaults to None in which case no data is saved.
        """
        if depth < 0:
            raise ValueError("Depth must be non-negative.")

        Crawler.logger.info(f"Starting `crawl_inner_pages` with args: {locals()}")

        # Start with the landing page
        urls_to_visit: deque[tuple[URL, int]] = deque([(URL(start_node), 0)])  # (url, depth)
        previous: dict[URL, Optional[str]] = {URL(start_node): None}  # map url to previous url
        redirects: set[URL] = set()  # set of URLs after redirect(s)
        domain = ""  # will be set after resolving landing page redirects

        # Graph search loop
        while urls_to_visit:
            current_url, current_depth = urls_to_visit.pop()  # DFS

            # Create uid for `current_url` if it does not exist
            if current_url not in self.uids:
                self.uids[current_url] = self.next_uid
                Path(self.data_path + f"{self.next_uid}/").mkdir(parents=True)

                self.next_uid += 1

            # Lookup uid
            uid = self.uids[current_url]
            if uid == -1:  # Indicates a duplicate URL that was discovered after redirection or a website that is down
                continue

            uid_data_path = self.data_path + f"{uid}/"
            site_info = f"'{current_url.url}' (UID: {uid})"  # for logging

            # Log site visit
            msg = f"Visiting: {site_info} at depth {current_depth}"
            Crawler.logger.info(msg)
            with open(uid_data_path + "logs.txt", "a") as file:
                file.write(msg + "\n")

            # Define request interceptor
            def interceptor(request: seleniumwire.request.Request):
                referer_interceptor = functools.partial(
                    interceptors.set_referer_interceptor,
                    url=current_url.url,
                    referer=previous.get(current_url),
                    data_path=uid_data_path
                )
                referer_interceptor(request)  # Intercept referer to previous page

                if cookie_blacklist:
                    remove_cookie_class_interceptor = functools.partial(
                        interceptors.remove_cookie_class_interceptor,
                        blacklist=cookie_blacklist,
                        data_path=uid_data_path
                    )
                    remove_cookie_class_interceptor(request)  # Intercept cookies

            # Set request interceptor
            self.driver.request_interceptor = interceptor

            # Remove previous HAR entries
            del self.driver.requests

            # Visit the current URL with exponential backoff reattempts
            attempt = 0
            wait_time = 0
            backoff_time = 0
            while attempt < self.total_get_attempts:
                try:
                    # Calculate wait time for exponential backoff
                    backoff_time = self.time_to_wait * (2 ** attempt)  # 5, 10, 20, ...
                    backoff_time = min(backoff_time, 60)  # Cap the maximum waiting time at 60 seconds

                    load_timeout = min(self.page_load_timeout + (attempt * 15), 60)
                    self.driver.set_page_load_timeout(load_timeout)  # Increase page load timeout by 15s with each attempt

                    # Attempt to get the website
                    self.driver.get(current_url.url)

                    break  # If successful, break out of the loop

                except TimeoutException:
                    attempt += 1
                    Crawler.logger.warning(f"Failed attempt {attempt}/{self.total_get_attempts}: {site_info}")
                    if attempt < self.total_get_attempts:
                        time.sleep(backoff_time)
                except Exception:
                    attempt += 1
                    Crawler.logger.exception(f"Failed attempt {attempt}/{self.total_get_attempts}: {site_info}")
                    if attempt < self.total_get_attempts:
                        time.sleep(backoff_time)

            if attempt == self.total_get_attempts:
                msg = f"Skipping down site: {site_info}"

                if current_depth == 0:
                    Crawler.logger.critical(msg)  # down landing page is more serious

                    if data is not None:
                        data["down"] = True
                else:
                    Crawler.logger.warning(msg)

                with open(self.data_path + "logs.txt", "a") as file:
                    file.write(msg + "\n")

                shutil.rmtree(uid_data_path)
                self.uids[current_url] = -1  # Website appears to be down, skip in future runs

                continue

            # Wait for redirects and dynamic content
            time.sleep(self.time_to_wait)

            # Get domain and CMP name
            if current_depth == 0:
                domain = utils.get_domain(self.driver.current_url)
                if data is not None:
                    with open("injections/cmp-detection.js", "r") as file:
                        js = file.read()

                    cmp_names = self.driver.execute_script(js)
                    data["cmp_names"] = [CMPType(name) for name in cmp_names]

            after_redirect = URL(self.driver.current_url)

            # Account for redirects
            if after_redirect in redirects:
                msg = f"Skipping duplicate site: {site_info}"
                Crawler.logger.warning(msg)
                with open(self.data_path + "logs.txt", "a") as file:
                    file.write(msg + "\n")

                shutil.rmtree(uid_data_path)
                self.uids[current_url] = -1  # Mark as duplicate
                continue

            redirects.add(after_redirect)

            # Account for domain name changes
            if after_redirect.domain() != domain:
                msg = f"Skipping domain redirect: {site_info}"
                Crawler.logger.warning(msg)
                with open(self.data_path + "logs.txt", "a") as file:
                    file.write(msg + "\n")

                shutil.rmtree(uid_data_path)
                self.uids[current_url] = -1
                continue

            # Save a screenshot of the viewport
            if crawl_name:
                self.save_viewport_screenshot(uid_data_path + f"{crawl_name}.png")

            # NOTE: We are assumming notice interaction propagates to all inner pages
            if current_depth == 0 and interaction_type is not None:
                if type(interaction_type) is BannerClickInteractionType:
                    status = bc.run_all_for_domain(domain, after_redirect.url, self.driver, interaction_type.value)

                    if status is None:
                        msg = f"BannerClick failed to {interaction_type.name}: {site_info}"
                        Crawler.logger.critical(msg)
                        with open(self.data_path + "logs.txt", "a") as file:
                            file.write(msg + "\n")

                    if data is not None:
                        data["click_success"] = status is not None

                if type(interaction_type) is CMPType:
                    if interaction_type == CMPType.ONETRUST:
                        with open("injections/onetrust.js", "r") as file:
                            js = file.read()

                        Crawler.logger.info(f"Injecting `onetrust.js`: {site_info}")
                        res = self.driver.execute_script(js)

                        if res["success"] is True:
                            Crawler.logger.info(f"Successfully injected OneTrust script: {res['message']}")
                        else:
                            Crawler.logger.error(f"Failed to inject OneTrust script: {res['message']}")

            # Save HAR file
            if crawl_name:
                self.save_har(uid_data_path + f"{crawl_name}.json")

            # Don't need to visit neighbors if we're at the maximum depth
            if current_depth == depth:
                continue

            # Find all the anchor elements (links) on the page
            a_elements = self.driver.find_elements(By.TAG_NAME, 'a')
            hrefs = [link.get_attribute('href') for link in a_elements]

            # Visit neighbors
            for neighbor in hrefs:
                if neighbor is None or utils.get_domain(neighbor) != domain or not validators.url(neighbor):  # type: ignore
                    # NOTE: Potential for false negatives if the href domain
                    # is different than the current domain but redirects to the current domain.
                    # However, this is unlikely to occur in practice and
                    # we do not want to visit every href present on the page.
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

    def save_har(self, file_path: str) -> None:
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

    def cleanup_driver(self) -> None:
        """Safely end the web driver."""
        self.driver.close()
        self.driver.quit()
