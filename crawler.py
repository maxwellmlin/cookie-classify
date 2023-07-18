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


class InteractionType(Enum):
    # Enum values correspond to BannerClick's `CHOICE` variable
    NO_ACTION = 0
    ACCEPT = 1
    REJECT = 2


class BannerClickStatus(Enum):
    FAIL = 0


class Crawler:
    """Crawl websites, intercept requests, and take screenshots."""

    def __init__(self, data_path: str, time_to_wait: int = 5, total_get_attempts: int = 3) -> None:
        """
        Args:
            data_path: Path to store log files and save screenshots.
            time_to_wait: Time to wait after visiting a page. Defaults to 5 seconds.
            total_get_attempts: Number of attempts to get a website. Defaults to 3.
        """
        options = FirefoxOptions()
        options.add_argument("--headless")  # TODO: native does not work

        seleniumwire_options = {
            'enable_har': True,
        }

        self.driver = webdriver.Firefox(options=options, seleniumwire_options=seleniumwire_options)

        self.time_to_wait = time_to_wait
        self.total_get_attempts = total_get_attempts

        self.data_path = data_path
        if not os.path.exists(data_path):
            os.mkdir(data_path)

        self.uids: dict[URL, int] = {}  # map url to a unique id
        self.next_uid = 0

    def crawl(self, url: str, depth: int = 2) -> None:
        """
        Crawl website with repeated calls to `crawl_inner_pages`.

        Args:
            url: URL of the website to crawl.
            depth: Number of layers of the DFS. Defaults to 2.
        """

        # Check if `url` results in redirects
        options = FirefoxOptions()
        options.add_argument("--headless")
        temp_driver = webdriver.Firefox(options=options)

        # Visit the current URL with multiple attempts
        attempt = 0
        for attempt in range(self.total_get_attempts):
            try:
                temp_driver.get(url)
                break  # If successful, break out of the loop

            except Exception as e:
                print(f"'{e}' on attempt {attempt+1}/{self.total_get_attempts} for website '{url}'.")
        if attempt == self.total_get_attempts - 1:
            msg = f"{self.total_get_attempts} attempts failed for '{url}'. Skipping."
            print(msg)
            with open(self.data_path + "logs.txt", "a") as file:
                file.write(msg + "\n")
            temp_driver.quit()
            return

        time.sleep(self.time_to_wait)

        domain = utils.get_domain(url)
        url_after_redirect = temp_driver.current_url
        domain_after_redirect = utils.get_domain(url_after_redirect)

        # NOTE: THIS WILL REMOVE ALL SITES THAT BANNERCLICK CANNOT REJECT
        status = bc.run_all_for_domain(domain_after_redirect, url_after_redirect, temp_driver, InteractionType.REJECT.value)
        temp_driver.quit()
        if not status:
            with open(self.data_path + "logs.txt", "a") as file:
                file.write("WARNING: BannerClick failed to click accept/reject button.\n")
            return

        if domain_after_redirect != domain:
            with open(self.data_path + "logs.txt", "a") as file:
                file.write(f"NOTE: Domain name changed from '{domain}' to '{domain_after_redirect}'.\n")
        if url_after_redirect != url:
            with open(self.data_path + "logs.txt", "a") as file:
                file.write(f"NOTE: URL changed from '{url}' to '{url_after_redirect}'.\n")

        # Collect cookies
        self.crawl_inner_pages(
            url_after_redirect,
            crawl_name="",
            depth=depth,
        )

        # Log
        self.crawl_inner_pages(
            url_after_redirect,
            crawl_name="normal",
            depth=depth,
        )

        # Click reject
        bc_status = self.crawl_inner_pages(
            url_after_redirect,
            crawl_name="",
            depth=0,
            interaction_type=InteractionType.REJECT,
        )

        if bc_status == BannerClickStatus.FAIL:
            # Delete all data
            for uid in self.uids.values():
                if uid == -1:
                    continue

                shutil.rmtree(self.data_path + f"{uid}/")

            return

        # Log
        self.crawl_inner_pages(
            url_after_redirect,
            crawl_name="after_reject",
            depth=depth,
        )

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
            cookie_blacklist: tuple[CookieClass, ...] = ()) -> Optional[BannerClickStatus]:
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

        Returns:
            BannerClickStatus.FAIL if the accept/reject button was not clicked successfully.
        """

        if depth < 0:
            raise ValueError("Depth must be non-negative.")

        print(f"Starting traversal with arguments: '{locals()}'.")

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
                msg = f"{self.total_get_attempts} attempts failed for '{current_url.url}' (UID: {uid}). Skipping."
                print(msg)
                with open(self.data_path + "logs.txt", "a") as file:
                    file.write(msg + "\n")

                shutil.rmtree(uid_data_path)
                self.uids[current_url] = -1  # Website appears to be down, skip in future runs
                del self.driver.request_interceptor
                continue

            # Wait for redirects and dynamic content
            time.sleep(self.time_to_wait)

            # Account for redirects
            after_redirect = URL(self.driver.current_url)
            if after_redirect in redirects:
                msg = f"Duplicate site '{after_redirect.url}' (UID: {uid}). Skipping."
                print(msg)
                with open(self.data_path + "logs.txt", "a") as file:
                    file.write(msg + "\n")

                shutil.rmtree(uid_data_path)
                self.uids[current_url] = -1  # Mark as duplicate
                continue

            redirects.add(after_redirect)

            # Account for domain name changes
            if after_redirect.domain() != domain:
                print("Redirect to different domain. Skipping...")
                continue

            # Save a screenshot of the viewport  # TODO: save full page screenshot
            if crawl_name:
                self.save_viewport_screenshot(uid_data_path + f"{crawl_name}.png")

            if current_depth == 0:  # NOTE: We are assumming bannerclick is successful on the landing page, and the notice disappears on inner pages
                if interaction_type.value:
                    status = bc.run_all_for_domain(domain, after_redirect.url, self.driver, interaction_type.value)
                    with open(uid_data_path + "logs.txt", "a") as file:
                        file.write(f"btn_status={status}" + "\n")

                    if not status:
                        with open(self.data_path + "logs.txt", "a") as file:
                            file.write("WARNING: BannerClick failed to click accept/reject button.\n")
                            return BannerClickStatus.FAIL

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
                    # is not the same as the current domain but redirects to the current domain.
                    # However, this is unlikely to occur in practice and
                    # we do not want to visit every href present on the page (`self.time_to_wait` penalty).
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

    def quit(self) -> None:
        """Safely end the web driver."""
        self.driver.quit()
