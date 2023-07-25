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

import bannerclick.bannerdetection as bc

import seleniumwire.request
from seleniumwire import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By

from cookie_database import CookieClass
import interceptors
import utils
from url import URL


class InteractionType(Enum):
    # Enum values correspond to BannerClick's `CHOICE` variable
    NO_ACTION = 0
    ACCEPT = 1
    REJECT = 2


class CrawlData(TypedDict):
    """
    Class for storing data about a crawl
    """

    data_path: str
    cmp_name: Optional[str]  # None if no cmp found
    click_success: Optional[bool]  # None if no click was attempted


class Crawler:
    """Crawl websites, intercept requests, and take screenshots."""

    def __init__(self, data_path: str, time_to_wait: int = 3, total_get_attempts: int = 3, page_load_timeout: int = 60, headless: bool = True) -> None:
        """
        Args:
            data_path: Path to store log files and save screenshots.
            time_to_wait: Time to wait after visiting a page. Defaults to 5 seconds.
            total_get_attempts: Number of attempts to get a website. Defaults to 3.
            page_load_timeout: Time to wait for a page to load. Defaults to 60 seconds.
            headless: Whether to run the web driver in headless mode. Defaults to True.
        """
        options = FirefoxOptions()

        self.headless = headless
        if headless:
            options.add_argument("--headless")

        seleniumwire_options = {
            'enable_har': True,
        }

        self.driver = webdriver.Firefox(options=options, seleniumwire_options=seleniumwire_options)
        self.page_load_timeout = page_load_timeout
        self.driver.set_page_load_timeout(page_load_timeout)

        self.time_to_wait = time_to_wait
        self.total_get_attempts = total_get_attempts

        self.data_path = data_path
        if not os.path.exists(data_path):
            os.mkdir(data_path)

        self.uids: dict[URL, int] = {}  # map url to a unique id
        self.next_uid = 0

    def crawl(self, url: str, depth: int = 2) -> CrawlData:
        """
        Crawl website with repeated calls to `crawl_inner_pages`.

        Args:
            url: URL of the website to crawl.
            depth: Number of layers of the DFS. Defaults to 2.
        """

        data: CrawlData = {"data_path": self.data_path,
                           "cmp_name": None,
                           "click_success": None}

        if not self.test_bannerclick(url, InteractionType.REJECT):
            data["click_success"] = False
            return data

        # Collect cookies
        self.crawl_inner_pages(
            url,
            crawl_name="",
            depth=depth,
            data=data
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
            crawl_name="",
            depth=0,
            interaction_type=InteractionType.REJECT,
            data=data
        )

        if not data.get("click_success"):
            # Delete all data
            for uid in self.uids.values():
                if uid == -1:
                    continue

                shutil.rmtree(self.data_path + f"{uid}/")

            return data

        # Log
        self.crawl_inner_pages(
            url,
            crawl_name="after_reject",
            depth=depth,
        )

        return data

        # blacklist = tuple([
        #     CookieClass.STRICTLY_NECESSARY,
        #     CookieClass.PERFORMANCE,
        #     CookieClass.FUNCTIONALITY,
        #     CookieClass.TARGETING,
        #     CookieClass.UNCLASSIFIED
        # ])

    def crawl_inner_pages(
            self,
            start_node: str,
            crawl_name: str = "",
            depth: int = 2,
            interaction_type: InteractionType = InteractionType.NO_ACTION,
            cookie_blacklist: tuple[CookieClass, ...] = (),
            data: Optional[CrawlData] = None):
        """
        Crawl inner pages of website with a given depth.

        Screenshot folder structure: domain/uid/crawl_name.png
        The domain is the domain of the url (before any redirect)
        to ensure consistency with the site list.

        Args:
            start_node: URL where traversal will begin. Future crawls will be constrained to this domain.
            crawl_name: Name of the crawl, used for path names. Defaults to "", where no data is saved.
            depth: Number of layers of the DFS. Defaults to 2.
            interaction_type: Whether to click the accept or reject button on cookie notices. Defaults to InteractionType.NO_ACTION.
            cookie_blacklist: A tuple of cookie classes to remove. Defaults to (), where no cookies are removed.
            data: Where crawl data is saved. Defaults to None in which case no data is saved.
        """

        if depth < 0:
            raise ValueError("Depth must be non-negative.")

        print(f"Starting traversal with arguments: '{locals()}'.")

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
                Path(self.data_path + f"{self.next_uid}/").mkdir(parents=True, exist_ok=True)

                self.next_uid += 1

            # Lookup uid
            uid = self.uids[current_url]
            if uid == -1:  # Indicates a duplicate URL that was discovered after redirection or a website that is down
                continue

            uid_data_path = self.data_path + f"{uid}/"

            # Log site visit
            msg = f"Visiting '{current_url.url}' (UID: {uid}) at depth {current_depth}."
            print(msg)
            if not os.path.isfile(uid_data_path + "logs.txt"):
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

            # Visit the current URL with multiple attempts
            attempt = 0
            for attempt in range(self.total_get_attempts):
                try:
                    self.driver.get(current_url.url)
                    break  # If successful, break out of the loop

                except Exception as e:
                    print(f"'{e}' on attempt {attempt+1}/{self.total_get_attempts} for inner page '{current_url.url}'.")
            if attempt == self.total_get_attempts - 1:
                msg = f"Skipping '{current_url.url}' (UID: {uid}). {self.total_get_attempts} attempts failed."
                print(msg)
                with open(self.data_path + "logs.txt", "a") as file:
                    file.write(msg + "\n")

                shutil.rmtree(uid_data_path)
                self.uids[current_url] = -1  # Website appears to be down, skip in future runs
                del self.driver.request_interceptor

                continue

            # Wait for redirects and dynamic content
            time.sleep(self.time_to_wait)

            # Get domain name
            if current_depth == 0:
                domain = utils.get_domain(self.driver.current_url)
                if data is not None:
                    data["cmp_name"] = self.get_cmp()

            # Account for redirects
            after_redirect = URL(self.driver.current_url)
            if after_redirect in redirects:
                msg = f"Skipping duplicate site '{current_url.url}' (UID: {uid})."
                print(msg)
                with open(self.data_path + "logs.txt", "a") as file:
                    file.write(msg + "\n")

                shutil.rmtree(uid_data_path)
                self.uids[current_url] = -1  # Mark as duplicate
                continue

            redirects.add(after_redirect)

            # Account for domain name changes
            if after_redirect.domain() != domain:
                msg = f"Skipping domain redirect '{current_url.url}' (UID: {uid})."
                print(msg)
                with open(self.data_path + "logs.txt", "a") as file:
                    file.write(msg + "\n")

                shutil.rmtree(uid_data_path)
                self.uids[current_url] = -1
                continue

            # Save a screenshot of the viewport
            if crawl_name:
                self.save_viewport_screenshot(uid_data_path + f"{crawl_name}.png")

            # NOTE: We are assumming bannerclick is successful on the landing page, and the notice disappears on inner pages
            if current_depth == 0:
                if interaction_type.value:
                    status = bc.run_all_for_domain(domain, after_redirect.url, self.driver, interaction_type.value)
                    if not status:
                        with open(self.data_path + "logs.txt", "a") as file:
                            file.write(f"BannerClick failed to {interaction_type.name}.\n")

                    if data is not None:
                        data["click_success"] = status is not None

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

            del self.driver.request_interceptor

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

    def get_cmp(self) -> Optional[str]:
        js = open("neverconsent/nc.js").read()
        self.driver.execute_script(js)

        time.sleep(self.time_to_wait)

        return self.driver.execute_script('return localStorage["nc_cmp"];')

    def test_bannerclick(self, url: str, interaction_type: InteractionType) -> bool:
        """
        Return whether the accept/reject button was clicked successfully.

        Args:
            url: URL of the website to test.
            interaction_type: Whether to click the accept or reject button on cookie notices.

        Returns:
            Whether the accept/reject button was clicked successfully.
        """

        options = FirefoxOptions()

        if self.headless:
            options.add_argument("--headless")

        driver = webdriver.Firefox(options=options)
        driver.set_page_load_timeout(self.page_load_timeout)

        # Visit the current URL with multiple attempts
        attempt = 0
        for attempt in range(self.total_get_attempts):
            try:
                driver.get(url)
                break  # If successful, break out of the loop

            except Exception as e:
                print(f"'{e}' on attempt {attempt+1}/{self.total_get_attempts} for website '{url}'.")
        if attempt == self.total_get_attempts - 1:
            msg = f"Skipping '{url}' (UID: 0). {self.total_get_attempts} attempts failed."
            print(msg)
            with open(self.data_path + "logs.txt", "a") as file:
                file.write(msg + "\n")
            driver.quit()

            return False

        time.sleep(self.time_to_wait)

        status = bc.run_all_for_domain(driver.current_url, utils.get_domain(driver.current_url), driver, interaction_type.value)
        driver.quit()

        if not status:
            with open(self.data_path + "logs.txt", "a") as file:
                file.write(f"BannerClick failed to {interaction_type.name}.\n")
                return False
        else:
            return True

    def quit(self) -> None:
        """Safely end the web driver."""
        self.driver.quit()
