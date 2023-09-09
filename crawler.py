import functools
from collections import deque
from enum import Enum
from pathlib import Path
from typing import Optional, TypedDict, Any
import os
import time
import shutil
import validators
import json
import logging
from collections.abc import Callable
import random

import bannerclick.bannerdetection as bc

import seleniumwire.request
from seleniumwire import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException, JavascriptException, NoSuchElementException

from cookie_database import CookieClass
import interceptors
import utils
from utils import log
from url import URL
import config


class BannerClick(str, Enum):
    """
    Type of interaction with Accept/Reject cookie notice.

    Enum values correspond to BannerClick's `CHOICE` variable.
    """

    ACCEPT = "BannerClick Accept"
    REJECT = "BannerClick Reject"


class CMP(str, Enum):
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
    cmp_names: set[CMP]  # Empty if no CMP found
    interaction_type: BannerClick | CMP | None  # None if no interaction was attempted
    interaction_success: Optional[bool]  # None if no interaction was attempted
    down: bool  # True if landing page is down or some other critical error occurred
    clickstream: list[str] | None  # List of CSS selectors that were clicked on


class CrawlDataEncoder(json.JSONEncoder):
    """
    Class for encoding `CrawlData` as JSON.
    """
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)

        # Default behavior for all other types
        return super().default(obj)


class Crawler:
    """
    Crawl websites, intercept requests, and take screenshots.
    """

    logger = logging.getLogger(config.LOGGER_NAME)

    def __init__(self, crawl_url: str, time_to_wait: int = 5, total_get_attempts: int = 3, page_load_timeout: int = 30, headless: bool = True) -> None:
        """
        Args:
            crawl_url: The URL of the website to crawl.
            time_to_wait: Time to wait between driver get requests. Defaults to 5 seconds.
            total_get_attempts: Number of attempts to get a website. Defaults to 3.
            page_load_timeout: Time to wait for a page to load. Defaults to 30 seconds.
            headless: Whether to run the web driver in headless mode. Defaults to True.
        """
        self.headless = headless
        self.page_load_timeout = page_load_timeout

        self.time_to_wait = time_to_wait
        self.total_get_attempts = total_get_attempts

        self.crawl_url = crawl_url

        self.data_path = f"{config.CRAWL_PATH}{utils.get_domain(crawl_url)}/"
        if not os.path.exists(self.data_path):
            os.mkdir(self.data_path)

        self.uids: dict[Any, int] = {}
        self.current_uid = 0

        self.data: CrawlData = {
            "data_path": self.data_path,
            "cmp_names": set(),
            "interaction_type": None,
            "interaction_success": None,
            "down": False,
            "clickstream": None
        }

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

    @staticmethod
    def crawl_method(crawl_algo: Callable[..., None]) -> Callable[..., CrawlData]:
        """
        Decorator that safely starts and ends the web driver as well as catches any exceptions.
        """
        def wrapper(*args, **kwargs) -> CrawlData:
            self = args[0]
            self.driver = self.get_driver()

            try:
                crawl_algo(*args, **kwargs)
            except Exception:  # skipcq: PYL-W0703
                Crawler.logger.critical(f"GENERAL CRAWL FAILURE: {self.crawl_url}", exc_info=True)

            self.cleanup_driver()

            return self.data

        return wrapper

    @crawl_method
    def compliance_algo(self, depth: int = 0):
        """
        Run the website cookie compliance algorithm.
        OneTrust CMP and Accept/Reject cookie notices are supported.

        Args:
            depth: Number of layers of the DFS. Defaults to 0.
        """
        # Uncomment for CMP Detection Only
        # self.crawl_inner_pages(
        #     data=data,
        # )
        # return data

        # Check cookie notice type
        self.crawl_inner_pages(
            interaction_type=BannerClick.REJECT,
        )

        #
        # Website Cookie Compliance Algorithm
        #
        if CMP.ONETRUST in self.data["cmp_names"]:
            self.cleanup_driver()
            self.driver = self.get_driver()

            #
            # OneTrust Compliance
            #

            # Collect cookies
            self.crawl_inner_pages(
                depth=depth
            )

            # Log
            self.crawl_inner_pages(
                crawl_name="no_interaction",
                depth=depth,
            )

            # OneTrust reject
            self.crawl_inner_pages(
                interaction_type=CMP.ONETRUST,
            )
            if not self.data["interaction_success"]:  # unable to BannerClick reject
                return

            # Log
            self.crawl_inner_pages(
                crawl_name="reject_only_tracking",
                depth=depth,
            )

            return

        if self.data["interaction_success"]:  # able to BannerClick reject
            self.cleanup_driver()
            self.driver = self.get_driver()  # Reset driver

            #
            # Accept/Reject Cookie Notices
            #

            # Collect cookies
            self.crawl_inner_pages(
                depth=depth
            )

            # Log
            self.crawl_inner_pages(
                crawl_name="normal",
                depth=depth,
            )

            # BannerClick reject
            self.crawl_inner_pages(
                interaction_type=BannerClick.REJECT,
            )
            if not self.data["interaction_success"]:  # unable to BannerClick reject
                msg = f"BannerClick failed to reject: {self.crawl_url}"
                Crawler.logger.critical(msg)
                with open(self.data_path + "logs.txt", "a") as file:
                    file.write(msg + "\n")

                return

            # Log
            self.crawl_inner_pages(
                crawl_name="after_reject",
                depth=depth,
            )

            return

    @crawl_method
    def classification_algo(self, trials: int = 10):
        """
        Cookie classification algorithm.

        trials: Number of clickstreams to generate. Defaults to 10.
        """
        for _ in range(trials):
            clickstream = self.crawl_clickstream(
                clickstream=None,
                crawl_name="all_cookies",
            )
            self.crawl_clickstream(
                clickstream=clickstream,
                crawl_name="no_cookies",
                cookie_blocklist=(
                    CookieClass.STRICTLY_NECESSARY,
                    CookieClass.PERFORMANCE,
                    CookieClass.FUNCTIONALITY,
                    CookieClass.TARGETING,
                    CookieClass.UNCLASSIFIED
                ),
            )

            self.current_uid += 1

    @log
    def crawl_inner_pages(
            self,
            crawl_name: str = "",
            depth: int = 0,
            interaction_type: BannerClick | CMP | None = None,
            cookie_blocklist: tuple[CookieClass, ...] = ()
    ):
        """
        Crawl inner pages of website with a given depth.

        Screenshot folder structure: domain/uid/crawl_name.png
        The domain is the domain of the url (before any redirect)
        to ensure consistency with the site list.

        Args:
            crawl_name: Name of the crawl, used for file names. Defaults to "", where no files are created.
            depth: Number of layers of the DFS. Defaults to 0.
            interaction_type: Type of interaction with cookie notice/API. Defaults to None, where no action is taken.
            cookie_blacklist: A tuple of cookie classes to remove. Defaults to (), where no cookies are removed.
        """
        if depth < 0:
            raise ValueError("Depth must be non-negative.")

        # Start with the landing page
        urls_to_visit: deque[tuple[URL, int]] = deque([(URL(self.crawl_url), 0)])  # (url, depth)
        previous: dict[URL, Optional[str]] = {URL(self.crawl_url): None}  # map url to previous url
        redirects: set[URL] = set()  # set of URLs after redirect(s)
        domain = ""  # will be set after resolving landing page redirects

        # Graph search loop
        while urls_to_visit:
            current_url, current_depth = urls_to_visit.pop()  # DFS

            # Create uid for `current_url` if it does not exist
            if current_url not in self.uids:
                self.uids[current_url] = self.current_uid
                Path(self.data_path + f"{self.current_uid}/").mkdir(parents=True)

                self.current_uid += 1

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

                if cookie_blocklist:
                    remove_cookie_class_interceptor = functools.partial(
                        interceptors.remove_cookie_class_interceptor,
                        blacklist=cookie_blocklist,
                        data_path=uid_data_path
                    )
                    remove_cookie_class_interceptor(request)  # Intercept cookies

            # Set request interceptor
            self.driver.request_interceptor = interceptor

            # Remove previous HAR entries
            del self.driver.requests

            # Visit the current URL with exponential backoff reattempts
            attempt = 0
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
                    self.data["down"] = True

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

                with open("injections/cmp-detection.js", "r") as file:
                    js = file.read()

                cmp_names = self.driver.execute_script(js)
                self.data["cmp_names"].update([CMP(name) for name in cmp_names])  # Taking union of detected CMPs

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
                self.data["interaction_type"] = interaction_type

                if type(interaction_type) is BannerClick:
                    if interaction_type == BannerClick.ACCEPT:
                        magic_number = 1
                    elif interaction_type == BannerClick.REJECT:
                        magic_number = 2

                    status = bc.run_all_for_domain(domain, after_redirect.url, self.driver, magic_number)
                    """
                    None = BannerClick failed

                    1 = Accept Success
                    2 = Reject Success

                    -1 = Accept (Settings) Success
                    -2 = Reject (Settings) Success
                    """
                    self.data["interaction_success"] = status is not None

                elif type(interaction_type) is CMP:
                    if interaction_type == CMP.ONETRUST:
                        injection_script = "onetrust.js"

                        with open(f"injections/{injection_script}", "r") as file:
                            js = file.read()

                        try:
                            result = self.driver.execute_script(js)
                        except JavascriptException as e:
                            result = {"success": False, "message": e}

                        Crawler.logger.info(f"Injecting '{injection_script}' on {site_info}")
                        if result["success"] is True:
                            Crawler.logger.info(f"Successfully injected with '{result['message']}'")
                        else:
                            Crawler.logger.critical(f"Failed to inject: {result['message']}")

                        self.data["interaction_success"] = result["success"]

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

    @log
    def crawl_clickstream(
            self,
            clickstream: list[str] | None,
            length: int = 10,
            crawl_name: str = "",
            cookie_blocklist: tuple[CookieClass, ...] = ()
    ) -> list[str]:
        """
        Crawl website using clickstream.

        Screenshot folder structure: domain/uid/crawl_name.png
        The domain is the domain of the url (before any redirect)
        to ensure consistency with the site list.

        Args:
            start_node: URL where traversal will begin. Future crawls will be constrained to this domain.
            clickstream: List of CSS selectors to click on. Defaults to None, where a clickstream is instead generated.
            length: Maximum length of the clickstream. Defaults to 10.
            crawl_name: Name of the crawl, used for file names. Defaults to "", where no files are created.
            cookie_blacklist: A tuple of cookie classes to remove. Defaults to (), where no cookies are removed.
        """
        if clickstream is None:
            clickstream = []
            generate_clickstream = True
        else:
            generate_clickstream = False

        if not generate_clickstream and length > len(clickstream):
            raise ValueError("Length must be less than or equal to the length of the clickstream.")

        uid_data_path = self.data_path + f"{self.current_uid}/"
        site_info = f"'{self.crawl_url}' (UID: {self.current_uid})"  # for logging

        # Define request interceptor
        def interceptor(request: seleniumwire.request.Request):
            if cookie_blocklist:
                remove_cookie_class_interceptor = functools.partial(
                    interceptors.remove_cookie_class_interceptor,
                    blacklist=cookie_blocklist,
                    data_path=uid_data_path
                )
                remove_cookie_class_interceptor(request)
        self.driver.request_interceptor = interceptor

        # Visit the current URL with exponential backoff reattempts
        attempt = 0
        backoff_time = 0
        while attempt < self.total_get_attempts:
            try:
                # Calculate wait time for exponential backoff
                backoff_time = self.time_to_wait * (2 ** attempt)  # 5, 10, 20, ...
                backoff_time = min(backoff_time, 60)  # Cap the maximum waiting time at 60 seconds

                load_timeout = min(self.page_load_timeout + (attempt * 15), 60)
                self.driver.set_page_load_timeout(load_timeout)  # Increase page load timeout by 15s with each attempt

                # Attempt to get the website
                self.driver.get(self.crawl_url)

                break  # If successful, break out of the loop

            except TimeoutException:
                attempt += 1
                Crawler.logger.warning(f"Failed attempt {attempt}/{self.total_get_attempts}: {self.crawl_url}")
                if attempt < self.total_get_attempts:
                    time.sleep(backoff_time)
            except Exception:
                attempt += 1
                Crawler.logger.exception(f"Failed attempt {attempt}/{self.total_get_attempts}: {self.crawl_url}")
                if attempt < self.total_get_attempts:
                    time.sleep(backoff_time)

        if attempt == self.total_get_attempts:
            msg = f"Skipping down site: {self.crawl_url}"
            Crawler.logger.critical(msg)
            with open(self.data_path + "logs.txt", "a") as file:
                file.write(msg + "\n")

            self.data["down"] = True

        # CMP detection
        # with open("injections/cmp-detection.js", "r") as file:
        #     js = file.read()
        # cmp_names = self.driver.execute_script(js)
        # self.data["cmp_names"].update([CMP(name) for name in cmp_names])  # Taking union of detected CMPs

        # Clickstream execution loop
        i = 0
        while i < length:
            if generate_clickstream:
                clickstream.append(self.get_clickstream_element())

            selector = clickstream[i]

            # Log site visit
            msg = f"Executing Clickstream #{i} for {site_info}"
            Crawler.logger.info(msg)
            with open(uid_data_path + "logs.txt", "a") as file:
                file.write(msg + "\n")

            #
            # Execute Clickstream
            #
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
            except NoSuchElementException:
                Crawler.logger.critical(f"Failed to find element: {selector}")
                self.data["interaction_success"] = False
                return clickstream

            try:
                element.click()

                Crawler.logger.info(f"Successfully clicked element: {selector}")
            except Exception:
                if generate_clickstream:
                    Crawler.logger.warning(f"Failed to click {selector}, generating new clickstream")
                    continue
                else:
                    Crawler.logger.critical(f"Failed to click: {selector}")
                    self.data["interaction_success"] = False
                    return clickstream

            # Wait for clickstream to execute
            time.sleep(self.time_to_wait)

            i += 1

        #
        # After clickstream
        #

        # Save a screenshot of the viewport
        if crawl_name:
            self.save_viewport_screenshot(uid_data_path + f"{crawl_name}.png")

        # Save HAR file
        if crawl_name:
            self.save_har(uid_data_path + f"{crawl_name}.json")

        self.data["clickstream"] = clickstream

        return clickstream

    def get_clickstream_element(self) -> str:
        """
        Return a CSS selector for a clickable element.

        Returns:
            CSS selector
        """
        with open("injections/clickable-elements.js", "r") as file:
            js = file.read()
        elements: list[str] = self.driver.execute_script(js)

        return random.choice(elements)

    def save_viewport_screenshot(self, file_path: str):
        """
        Save a screenshot of the viewport to a file.

        Args:
            file_path: Path to save the screenshot.
        """
        # Take a screenshot of the viewport
        try:
            # NOTE: Rarely, this command will fail
            # See: https://bugzilla.mozilla.org/show_bug.cgi?id=1493650
            screenshot = self.driver.get_screenshot_as_png()
        except WebDriverException:
            Crawler.logger.exception("Failed to take screenshot")
            return

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
        """
        Safely end the web driver.
        """
        self.driver.close()
        self.driver.quit()
