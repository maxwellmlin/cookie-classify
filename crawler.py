import functools
from collections import deque
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import Optional, TypedDict, Any
import pathlib
import time
import shutil
import validators
import json
import logging
import random

import seleniumwire.request
from seleniumwire import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    JavascriptException,
    NoSuchElementException,
    ElementNotInteractableException,
    ElementClickInterceptedException,
    InvalidSelectorException,
    StaleElementReferenceException
)

import bannerclick.bannerdetection as bc

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


DriverAction = Enum(
    "DriverAction", [
        "BACK"  # Go back to the previous page
    ]
)


class CrawlData(TypedDict):
    """
    Class for storing data about a crawl.
    """

    data_path: str
    cmp_names: set[CMP] | None  # Empty if no CMP found
    interaction_type: BannerClick | CMP | None  # None if no interaction was attempted
    interaction_success: bool | None  # None if no interaction was attempted
    down: bool | None  # True if landing page is down or some other critical error occurred
    clickstream: list[list[str | DriverAction] | None] | None  # List of CSS selectors that were clicked on


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
        self.driver: webdriver.Firefox

        self.headless = headless
        self.page_load_timeout = page_load_timeout

        self.time_to_wait = time_to_wait
        self.total_get_attempts = total_get_attempts

        self.crawl_url = crawl_url

        self.data_path = f"{config.CRAWL_PATH}{utils.get_domain(crawl_url)}/"
        pathlib.Path(self.data_path).mkdir(parents=True, exist_ok=False)

        self.uids: dict[Any, int] = {}
        self.current_uid = 0

        self.data: CrawlData = {
            "data_path": self.data_path,
            "cmp_names": None,
            "interaction_type": None,
            "interaction_success": None,
            "down": None,
            "clickstream": None
        }

    def get_driver(self, enable_har: bool = True) -> webdriver.Firefox:
        """
        Initialize and return a Firefox web driver using arguments from `self`.

        Args:
            enable_har: Whether to enable HAR logging. Defaults to True.
        """
        options = FirefoxOptions()

        # See: https://stackoverflow.com/a/64724390/21055641
        options.add_argument("--disable-extensions")
        options.add_argument('--disable-application-cache')
        options.add_argument('--disable-gpu')

        if self.headless:
            options.add_argument("--headless")

        seleniumwire_options = {
            'enable_har': enable_har,
        }

        driver = webdriver.Firefox(options=options, seleniumwire_options=seleniumwire_options)
        driver.set_page_load_timeout(self.page_load_timeout)

        return driver

    @staticmethod
    def crawl_method(func: Callable[..., None]) -> Callable[..., CrawlData]:
        """
        Decorator that safely ends the web driver and catches any exceptions.
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> CrawlData:
            self = args[0]

            try:
                func(*args, **kwargs)
            except Exception:  # skipcq: PYL-W0703
                Crawler.logger.critical(f"GENERAL CRAWL EXCEPTION: {self.crawl_url}", exc_info=True)

            self.driver.quit()

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
        self.driver = self.get_driver()

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
        if self.data["cmp_names"] and CMP.ONETRUST in self.data["cmp_names"]:
            self.driver.quit()
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
            self.driver.quit()
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

        Args:
            trials: Number of clickstreams to generate. Defaults to 10.
        """

        self.data["clickstream"] = list()
        for _ in range(trials):
            Path(self.data_path + f"{self.current_uid}/").mkdir(parents=True)

            self.driver = self.get_driver(enable_har=False)
            clickstream = self.crawl_clickstream(
                clickstream=None,
                crawl_name="all_cookies",
            )
            self.driver.quit()
            self.data["clickstream"].append(clickstream)

            with open(f'{self.data_path}/{self.current_uid}/results.json', 'w') as log_file:
                json.dump(self.data, log_file, cls=CrawlDataEncoder)

            self.driver = self.get_driver(enable_har=False)
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
            self.driver.quit()

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

                    if current_depth == 0:
                        self.data["down"] = False

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

                cmp_names = [CMP(name) for name in self.driver.execute_script(js)]

                if self.data["cmp_names"] is None:
                    self.data["cmp_names"] = set(cmp_names)
                else:
                    self.data["cmp_names"].update(cmp_names)  # Taking union of detected CMPs

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
            clickstream: list[str | DriverAction] | None,
            length: int = 10,
            crawl_name: str = "",
            cookie_blocklist: tuple[CookieClass, ...] = ()
    ) -> list[str | DriverAction] | None:
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

        Returns:
            The clickstream that was executed. None if clickstream execution failed.
        """
        if clickstream is None:
            clickstream = []
            generate_clickstream = True
        else:
            generate_clickstream = False

        uid_data_path = self.data_path + f"{self.current_uid}/"

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

                self.data["down"] = False

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
            return None

        domain = utils.get_domain(self.driver.current_url)
        original_url = self.driver.current_url

        # Clickstream execution loop
        i = 1

        selectors: list[str] = self.get_selectors()
        clickstream_length = length if generate_clickstream else min(length, len(clickstream))
        while i <= clickstream_length:
            # No more possible actions
            if len(selectors) == 0 and self.driver.current_url == original_url:
                return clickstream

            # Close all tabs except the first one
            while len(self.driver.window_handles) > 1:
                self.driver.switch_to.window(self.driver.window_handles[1])
                self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

            # Restrict within original domain
            while utils.get_domain(self.driver.current_url) != domain:
                self.driver.back()

            if generate_clickstream:
                # Randomly click on an element; if all elements have been exhausted, go back
                if selectors:
                    action = selectors.pop(random.randrange(len(selectors)))
                else:
                    action = DriverAction.BACK
            else:
                action = clickstream[i]

            #
            # Execute Clickstream
            #
            if type(action) is DriverAction:
                if action == DriverAction.BACK:
                    self.driver.back()
                Crawler.logger.info("All selectors exhausted. Navigating to previous page.")

            else:
                try:
                    # Find element
                    element = self.driver.find_element(By.CSS_SELECTOR, action)
                    # Scroll to element
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    # Click
                    element.click()

                except (NoSuchElementException, ElementNotInteractableException, ElementClickInterceptedException, InvalidSelectorException, StaleElementReferenceException):
                    if generate_clickstream:
                        Crawler.logger.debug(f"{len(selectors)} potential selectors remaining")
                        continue

                    Crawler.logger.critical(f"Failed clickstream {self.current_uid} on action {i}/{clickstream_length}", exc_info=True)
                    self.data["interaction_success"] = False
                    return clickstream

                Crawler.logger.info(f"Completed action {i}/{clickstream_length}")
                if generate_clickstream:
                    clickstream.append(action)
                    selectors = self.get_selectors()
            i += 1

        Crawler.logger.info(f"Completed clickstream {self.current_uid}")

        #
        # After clickstream
        #

        # Save a screenshot of the viewport
        if crawl_name:
            self.save_viewport_screenshot(uid_data_path + f"{crawl_name}.png")

        return clickstream

    def get_selectors(self) -> list[str]:
        """
        Return a list of CSS selectors for clickable elements on the page.
        """
        with open("injections/clickable-elements.js", "r") as file:
            js = file.read()

        selectors: list[str] = self.driver.execute_script(js)

        return selectors

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
