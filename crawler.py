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

from utils.cookie_database import CookieClass
import utils.interceptors as interceptors
import utils.utils as utils
from utils.utils import log
from utils.url import URL
import config


class BannerClick(str, Enum):
    """
    Type of BannerClick interaction with Accept/Reject cookie notice.
    """

    ACCEPT = "BannerClick Accept"
    REJECT = "BannerClick Reject"


class ClickableElement(str, Enum):
    """
    Type of clickable element.
    See clickable-elements.js for definitions.
    """

    BUTTON = "button"
    LINK = "link"
    ONCLICK = "onclick"
    POINTER = "pointer"


class CMP(str, Enum):
    """
    Type of CMP API.

    Enum values correspond to the name of the exposed CMP JavaScript API object.
    """

    ONETRUST = "OneTrust"
    TCF = "__tcfapi"


class DriverAction(str, Enum):
    """
    Type of action to take on the driver.
    """

    BACK = "driver.back"  # Go back to the previous page

class LandingPageDown(Exception):
    """
    This exception is raised when the landing page is down.
    @crawl_algo catches this exception.
    
    If an inner page is down, the crawler should continue traversing the website,
    going back to the previous page if necessary. However, if the landing page is down,
    no data can be generated at all. Therefore, this exception is raised to indicate
    that the website should be skipped in the analysis.
    """
    pass

class UrlDown(Exception):
    """
    This exception is raised in self.get if the URL cannot be accessed.
    
    If appropriate, this exception should be escalated to LandingPageDown.
    """
    pass

class CrawlResults(TypedDict):
    """
    Class for storing results about a crawl.
    """

    url: str | None  # URL of the website being crawled. None if Domain->URL resolution failed.
    data_path: str  # Where the crawl data is stored
    landing_page_down: bool | None  # True/False if landing page is down/up, None if not attempted
    unexpected_exception: bool  # True iff an unexpected exception occurred
    total_time: int | None  # Time to crawl the website, initialized to None
    SLURM_ARRAY_TASK_ID: int | None  # Set by main.py

    # Only set during compliance_algo
    cmp_names: set[CMP] | None  # Empty if no CMPs found, None if CMP detection not attempted
    interaction_type: BannerClick | CMP | None  # None if no interaction was attempted
    interaction_success: bool | None  # None if no interaction was attempted

    # Only set during classification_algo
    # List of clickstreams where each clickstream is a list of CSS selectors (str) or DriverActions
    # Each CSS selector is paired with the type of element that was clicked (see clickable-elements.js)
    # Each DriverAction is paired with None
    clickstream: list[list[tuple[str | DriverAction, ClickableElement | None]]] | None
    traversal_failures: dict[ClickableElement, int] # Number of click failures for each type of click


class CrawlDataEncoder(json.JSONEncoder):
    """
    Class for encoding CrawlData as JSON.
    """
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)

        # Default behavior for all other types
        return super().default(obj)


class Crawler:
    """
    Crawl websites, intercept requests, and take screenshots.
    
    Crawl algorithms are decorated by @crawl_algo.
    See README.md for more information.
    """

    logger = logging.getLogger(config.LOGGER_NAME)

    def __init__(self, domain: str, time_to_wait: int = 5, total_get_attempts: int = 3, page_load_timeout: int = 60, headless: bool = True) -> None:
        """
        Args:
            crawl_url: The URL of the website to crawl.
            time_to_wait: Time to wait between actions. Defaults to 10 seconds.
            total_get_attempts: Number of attempts to get a website. Defaults to 3.
            page_load_timeout: Time to wait for a page to load. Defaults to 60 seconds.
            headless: Whether to run the web driver in headless mode. Defaults to True.
        """
        self.start_time = time.time()

        self.driver: webdriver.Firefox

        self.headless = headless
        self.page_load_timeout = page_load_timeout

        self.time_to_wait = time_to_wait
        self.total_get_attempts = total_get_attempts

        self.domain = domain
        self.url = None # Must be resolved in a crawl_algo

        # Where the crawl data is stored
        self.data_path = f"{config.CRAWL_PATH}{domain}/"
        pathlib.Path(self.data_path).mkdir(parents=True, exist_ok=False)

        # Each URL is assigned a unique ID
        self.uids: dict[Any, int] = {}
        self.current_uid = 0

        # Each clickstream is assigned a unique ID
        self.clickstream = 1

        self.results: CrawlResults = {
            "url": None,
            "data_path": self.data_path,
            "landing_page_down": None,
            "unexpected_exception": False,
            "total_time": None,
            "SLURM_ARRAY_TASK_ID": None,

            "cmp_names": None,
            "interaction_type": None,
            "interaction_success": None,

            "clickstream": None,
            "traversal_failures": {
                ClickableElement.BUTTON: 0,
                ClickableElement.LINK: 0,
                ClickableElement.ONCLICK: 0,
                ClickableElement.POINTER: 0,
            }
        }

    def get_driver(self, enable_har: bool = True) -> webdriver.Firefox:
        """
        Initialize and return a Firefox web driver using arguments from self.

        Args:
            enable_har: Whether to enable HAR logging. Defaults to True.
            disable_cookies: Whether to disable cookies. Defaults to False.
        """
        options = FirefoxOptions()

        # See: https://stackoverflow.com/a/64724390/21055641
        # options.add_argument("--disable-extensions")
        # options.add_argument('--disable-application-cache')
        # options.add_argument('--disable-gpu')

        if self.headless:
            options.add_argument("--headless")

        seleniumwire_options = {
            'enable_har': enable_har,
        }

        firefox_profile = webdriver.FirefoxProfile()  # by default, will create a fresh profile

        driver = webdriver.Firefox(options=options, seleniumwire_options=seleniumwire_options, firefox_profile=firefox_profile)
        driver.set_page_load_timeout(self.page_load_timeout)

        return driver

    @staticmethod
    def crawl_algo(func: Callable[..., None]) -> Callable[..., CrawlResults]:
        """
        Decorator that safely ends the web driver and catches any exceptions.
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> CrawlResults:
            self = args[0]

            try:
                func(*args, **kwargs)
            except LandingPageDown:
                Crawler.logger.critical(f"Landing page is down for '{self.domain}'.")
                self.results["landing_page_down"] = True
            except Exception:  # skipcq: PYL-W0703
                Crawler.logger.critical(f"Unexpected exception for '{self.domain}'.", exc_info=True)
                self.results["unexpected_exception"] = True

            self.driver.quit()

            self.results["total_time"] = time.time() - self.start_time

            return self.results

        return wrapper

    def get(self, url: str) -> str:
        """
        Get the website at the given URL with multiple reattempts.

        Args:
            url: The URL of the website to get.

        Raises:
            UrlDown: If the url cannot be accessed.
            
        Returns:
            The final resolved URL of the website.
        """
        # Visit the url with reattempts
        for attempt in range(self.total_get_attempts):
            try:
                # Attempt to get the website
                self.driver.get(url)
                time.sleep(self.time_to_wait)
                break  # If successful, break out of the loop

            except TimeoutException:
                Crawler.logger.warning(f"Failed get attempt {attempt}/{self.total_get_attempts} for '{url}'.")
            except Exception:
                Crawler.logger.warning(f"Failed get attempt {attempt}/{self.total_get_attempts} for '{url}'.", exc_info=True)

            if attempt != self.total_get_attempts - 1:
                time.sleep(self.time_to_wait)
        else:
            # Unable to get the website after all attempts
            raise UrlDown()

        # If there are no clickable elements, the website is down
        selectors: list[tuple[str, str]] = list(zip(*self.inject_script("injections/clickable-elements.js")))
        if len(selectors) == 0:
            raise UrlDown()
        
        return self.driver.current_url

    def resolve_domain(self, domain: str) -> str:
        """
        Resolve a domain to a URL.

        Args:
            domain: The domain to resolve.
        """
        for url in [f"https://{domain}", f"https://www.{domain}", f"http://{domain}", f"http://www.{domain}"]:
            try:
                return self.get(url)
            except UrlDown:
                continue
        
        raise LandingPageDown()

    @crawl_algo
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
        if self.results["cmp_names"] and CMP.ONETRUST in self.results["cmp_names"]:
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
            if not self.results["interaction_success"]:  # unable to BannerClick reject
                return

            # Log
            self.crawl_inner_pages(
                crawl_name="reject_only_tracking",
                depth=depth,
            )

            return

        if self.results["interaction_success"]:  # able to BannerClick reject
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
            if not self.results["interaction_success"]:  # unable to BannerClick reject
                Crawler.logger.critical(f"BannerClick failed to reject '{self.url}'.")
                return

            # Log
            self.crawl_inner_pages(
                crawl_name="after_reject",
                depth=depth,
            )

            return

    @crawl_algo
    def classification_algo(self, total_actions: int = 50, clickstream_length: int = 5, control_screenshots: int = 1):
        """
        Cookie classification algorithm.

        Args:
            trials: Number of clickstreams to generate. Defaults to 10.
            length: Length of each clickstream. Defaults to 5.
            screenshots: Number of screenshots to take for the control group. Defaults to 10.
        """

        # Domain -> URL Resolution
        self.driver = self.get_driver(enable_har=False)
        self.url = self.resolve_domain(self.domain)
        self.results["url"] = self.url
        self.logger.info(f"Resolved domain '{self.domain}' to '{self.url}'.")
        self.driver.quit()

        # Classification Algorithm
        current_actions = 0
        while current_actions < total_actions:
            clickstream_path = self.data_path + f"{self.clickstream}/"
            Path(clickstream_path).mkdir(parents=True)

            self.driver = self.get_driver()
            clickstream = self.crawl_clickstream(
                clickstream=None,
                clickstream_length=clickstream_length,
                crawl_name="baseline",
                set_request_interceptor=False,
                screenshots=1,
            )
            self.save_har(clickstream_path + "baseline.json")
            self.driver.quit()

            if self.results["clickstream"] is not None:
                self.results["clickstream"].append(clickstream)
            else:
                self.results["clickstream"] = [clickstream]

            # Control group
            self.driver = self.get_driver()
            control_clickstream = self.crawl_clickstream(
                clickstream=clickstream,
                clickstream_length=clickstream_length,
                crawl_name="control",
                set_request_interceptor=False,
                screenshots=control_screenshots,
            )
            current_actions += len(control_clickstream) + 1 # We add one since we count just getting the website as an action
            self.save_har(clickstream_path + "control.json")
            self.driver.quit()

            # Experimental group
            self.driver = self.get_driver()
            self.crawl_clickstream(
                clickstream=clickstream,
                clickstream_length=clickstream_length, # No need to traverse more than the control group
                crawl_name="experimental",
                set_request_interceptor=True,
                screenshots=1,
            )
            self.save_har(clickstream_path + "experimental.json")
            self.driver.quit()

            Crawler.logger.info(f"Data collected for {current_actions}/{total_actions} actions.")

            self.clickstream += 1

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
        urls_to_visit: deque[tuple[URL, int]] = deque([(URL(self.url), 0)])  # (url, depth)
        previous: dict[URL, Optional[str]] = {URL(self.url): None}  # map url to previous url
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
            Crawler.logger.info(f"Visiting '{site_info}' at depth {current_depth}.")

            # Define request interceptor
            def request_interceptor(request: seleniumwire.request.Request):
                old_header = request.headers["Cookie"]

                referer_interceptor = functools.partial(
                    interceptors.set_referer_interceptor,
                    url=current_url.url,
                    referer=previous.get(current_url),
                )
                referer_interceptor(request)  # Intercept referer to previous page

                if cookie_blocklist:
                    remove_cookie_class_interceptor = functools.partial(
                        interceptors.remove_cookie_class_interceptor,
                        blacklist=cookie_blocklist,
                    )
                    remove_cookie_class_interceptor(request)  # Intercept cookies

            # Set request interceptor
            self.driver.request_interceptor = request_interceptor

            # Remove previous HAR entries
            del self.driver.requests

            # Visit the current URL with reattempts
            attempt = 0
            while attempt < self.total_get_attempts:
                try:
                    # Attempt to get the website
                    self.driver.get(current_url.url)

                    if current_depth == 0:
                        self.results["landing_page_down"] = False

                    break  # If successful, break out of the loop

                except TimeoutException:
                    attempt += 1
                    Crawler.logger.warning(f"Failed attempt {attempt}/{self.total_get_attempts} for {site_info}.")
                    if attempt < self.total_get_attempts:
                        time.sleep(self.time_to_wait)
                except Exception:
                    attempt += 1
                    Crawler.logger.exception(f"Failed attempt {attempt}/{self.total_get_attempts} for {site_info}.")
                    if attempt < self.total_get_attempts:
                        time.sleep(self.time_to_wait)

            if attempt == self.total_get_attempts:
                if current_depth == 0:
                    raise LandingPageDown()
                else:
                    Crawler.logger.warning(f"Skipping down site '{site_info}'.")

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

                if self.results["cmp_names"] is None:
                    self.results["cmp_names"] = set(cmp_names)
                else:
                    self.results["cmp_names"].update(cmp_names)  # Taking union of detected CMPs

            after_redirect = URL(self.driver.current_url)

            # Account for redirects
            if after_redirect in redirects:
                Crawler.logger.warning(f"Skipping duplicate site '{site_info}'.")

                shutil.rmtree(uid_data_path)
                self.uids[current_url] = -1  # Mark as duplicate
                continue

            redirects.add(after_redirect)

            # Account for domain name changes
            if after_redirect.domain() != domain:
                Crawler.logger.warning(f"Skipping domain redirect '{site_info}'.")

                shutil.rmtree(uid_data_path)
                self.uids[current_url] = -1
                continue

            # Save a screenshot of the viewport
            if crawl_name:
                self.save_screenshot(uid_data_path + f"{crawl_name}")

            # NOTE: We are assumming notice interaction propagates to all inner pages
            if current_depth == 0 and interaction_type is not None:
                self.results["interaction_type"] = interaction_type

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
                    self.results["interaction_success"] = status is not None

                elif type(interaction_type) is CMP:
                    if interaction_type == CMP.ONETRUST:
                        injection_script = "onetrust.js"

                        with open(f"injections/{injection_script}", "r") as file:
                            js = file.read()

                        try:
                            result = self.driver.execute_script(js)
                        except JavascriptException as e:
                            result = {"success": False, "message": e}

                        Crawler.logger.info(f"Injecting '{injection_script}' on {site_info}.")
                        if result["success"] is True:
                            Crawler.logger.info(f"Successfully injected groups field '{result['message']}'.")
                        else:
                            Crawler.logger.critical(f"Failed to inject groups field. {result['message']}")

                        self.results["interaction_success"] = result["success"]

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
            clickstream: list[tuple[str | DriverAction, ClickableElement | None]] | None,
            clickstream_length: int = 5,
            crawl_name: str = "",
            set_request_interceptor: bool = False,
            screenshots: int = 1
    ) -> list[tuple[str | DriverAction, ClickableElement | None]]:
        """
        Crawl website using clickstream.

        Args:
            start_node: URL where traversal will begin.
            clickstream: List of CSS selectors/driver actions and their corresponding type. Defaults to None, where a clickstream is instead generated.
            clickstream_length: Maximum length of the clickstream. Defaults to 5.
            crawl_name: Name of the crawl, used for file names. Defaults to "", where no files are created.
            set_request_interceptor: Whether to set the request interceptor. Defaults to False.
            screenshots: Number of screenshots to take. Defaults to 1.

        Returns:
            The clickstream that was generated/traversed.
        """
        if clickstream is None:
            clickstream = []
            generate_clickstream = True
        else:
            generate_clickstream = False

        clickstream_path = self.data_path + f"{self.clickstream}/"

        if set_request_interceptor:
            # Define request interceptor
            def request_interceptor(request: seleniumwire.request.Request):
                interceptors.remove_third_party_interceptor(request, self.url)
                # interceptors.remove_all_interceptor(request)
            self.driver.request_interceptor = request_interceptor
        else:
            del self.driver.request_interceptor

        try:
            original_url = self.get(self.url)
            self.results["landing_page_down"] = False
        except UrlDown:
            raise LandingPageDown()

        domain = utils.get_domain(original_url)

        self.driver.execute_script("window.scrollTo(0, 0);")
        if crawl_name:
            self.extract_features(clickstream_path, crawl_name)
            self.save_screenshot(clickstream_path + f"{crawl_name}-0", screenshots=screenshots)

        # Clickstream execution loop
        selectors: list[tuple[str, str]] = list(zip(*self.inject_script("injections/clickable-elements.js"))) if generate_clickstream else []
        clickstream_length = clickstream_length if generate_clickstream else min(clickstream_length, len(clickstream))  # cannot exceed length of clickstream
        i = 0
        while i < clickstream_length:  # Note: we need a while loop here since we don't want to increment i if we fail to click
            # No more possible actions
            if generate_clickstream and not selectors and self.driver.current_url == original_url:
                Crawler.logger.critical(f"Unable to generate full clickstream. Generated length is {len(clickstream)}/{clickstream_length}.")
                return clickstream

            element_type = None
            if generate_clickstream:
                # Randomly click on an element; if all elements have been exhausted, go back
                if selectors:
                    action, _element_type = selectors.pop(random.randrange(len(selectors)))
                    element_type = ClickableElement(_element_type)
                else:
                    action = DriverAction.BACK
            else:
                action, element_type = clickstream[i]

            #
            # Execute clickstream
            #
            if type(action) is DriverAction:
                if action == DriverAction.BACK:
                    self.back()

            else:
                try:
                    # Find element
                    element = self.driver.find_element(By.CSS_SELECTOR, action)
                    # Click
                    element.click()
                except (
                    NoSuchElementException,
                    ElementNotInteractableException,
                    ElementClickInterceptedException,
                    InvalidSelectorException,
                    StaleElementReferenceException,
                    TimeoutException,
                    WebDriverException
                ):
                    if generate_clickstream:
                        continue
                    else:  # skipcq: PYL-R1724
                        # Failure when traversing clickstream
                        Crawler.logger.critical(f"Failed traversing clickstream {self.clickstream} ({crawl_name}) on action {i+1}/{clickstream_length}.")

                        if element_type is not None:
                            self.results["traversal_failures"][element_type] += 1

                        return clickstream[:i]

            Crawler.logger.info(f"Completed action {i+1}/{clickstream_length}.")
            time.sleep(self.time_to_wait)

            # Close all tabs except the first one
            while len(self.driver.window_handles) > 1:
                self.driver.switch_to.window(self.driver.window_handles[1])
                self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

            # Restrict within original domain
            while utils.get_domain(self.driver.current_url) != domain:
                self.back()

            # Extract data
            self.driver.execute_script("window.scrollTo(0, 0);")
            if crawl_name:
                self.extract_features(clickstream_path, crawl_name)
                self.save_screenshot(clickstream_path + f"{crawl_name}-{i+1}", screenshots=screenshots)

            # Save action and generate new action
            if generate_clickstream:
                clickstream.append((action, element_type))
                selectors = list(zip(*self.inject_script("injections/clickable-elements.js")))
            
            i += 1

        Crawler.logger.info(f"Completed clickstream {self.clickstream} ({crawl_name}).")

        return clickstream

    def inject_script(self, path: str) -> Any:
        """
        Inject a JavaScript file into the current page.
        """
        with open(path, "r") as file:
            js = file.read()

        return self.driver.execute_script(js)

    def save_screenshot(self, file_name: str, full_page: bool = False, screenshots: int = 1, delay: int = 1) -> None:
        """
        Save a screenshot of the viewport to a file.

        Args:
            file_name: Screenshot name.
            full_page: Whether to take a screenshot of the entire page. Defaults to False.
            screenshots: Number of screenshots to take. Defaults to 1.
            delay: Time to wait between screenshots. Defaults to 1 second.
        """
        for i in range(screenshots):
            if screenshots > 1:
                file_path = f"{file_name}-{i+1}.png"
            else:
                file_path = f"{file_name}.png"

            if full_page:
                el = self.driver.find_element_by_tag_name('body')
                el.screenshot(file_path)
            else:
                # Take a screenshot of the viewport
                try:
                    # NOTE: Rarely, this command will fail
                    # See: https://bugzilla.mozilla.org/show_bug.cgi?id=1493650
                    screenshot = self.driver.get_screenshot_as_png()
                except WebDriverException:
                    Crawler.logger.exception("Failed to take screenshot.")
                    return

                # Save the screenshot to a file
                with open(file_path, "wb") as file:
                    file.write(screenshot)

            if i < screenshots - 1:
                time.sleep(delay)

    def extract_features(self, path: pathlib.Path | str, crawl_name: str) -> None:
        """
        Extract features from the current page and save them to a file.

        Args:
            path: Directory to save the content.
            crawl_name: Name of the crawl (e.g., "baseline", "control", "experimental") used for file names.
        """
        def extract_word_counts(innerText: str):
            """
            Extract words from innerText and return a dictionary of word counts.
            
            Args:
                innerText: The innerText of the page.
            """
            words = []
            lines = innerText.splitlines()
            for line in lines:
                words.extend(line.split())

            counts: dict[str, int] = {}
            for word in words:
                if word in counts:
                    counts[word] += 1
                else:
                    counts[word] = 1
            return counts
        
        def count_list_items(list: list) -> dict:
            """
            Reduce a list to a dictionary of frequencies.
            """
            frequencies: dict = {}
            for item in list:
                if item in frequencies:
                    frequencies[item] += 1
                else:
                    frequencies[item] = 1
            return frequencies

        if isinstance(path, str):
            path = pathlib.Path(path)

        data_path = path / "features.json"

        content = {
            "innerText": extract_word_counts(self.inject_script("injections/inner-text.js")),
            "links": count_list_items(self.inject_script("injections/links.js")),
            "img": count_list_items(self.inject_script("injections/img.js")),
        }

        if (data_path).exists():
            with open(data_path, "r") as file:
                data = json.load(file)
        else:
            data = {}

        for name, extract in content.items():
            if name not in data:
                data[name] = {}
            if crawl_name not in data[name]:
                data[name][crawl_name] = []

            data[name][crawl_name].append(extract)

        with open(data_path, 'w') as file:
            json.dump(data, file)

    def save_har(self, file_path: str) -> None:
        """
        Save current HAR file to file_path.

        NOTE: Requests continually get logged to the same HAR file.
        To start logging a new HAR file, use: 'del self.driver.requests'.

        Args:
            file_path: Path to save the HAR file. The file extension should be '.json'.
        """
        if not file_path.lower().endswith(".json"):
            raise ValueError("File extension must be `.json`.")

        data = json.loads(self.driver.har)

        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)

    def back(self) -> None:
        """
        Go back to the previous page.
        """
        try:
            self.driver.back()
        except (TimeoutException, WebDriverException):
            # Use JavaScript to go back if the driver fails
            self.driver.execute_script("window.history.go(-1)")

    def __repr__(self) -> str:
        """
        Return crawl_url in logs.
        """
        return self.url
