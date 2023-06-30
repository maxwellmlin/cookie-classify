from typing import Optional

import seleniumwire.request

from cookie_request_header import CookieRequestHeader
from url import URL

"""
Interceptors for seleniumwire.

NOTE: Many of these functions are general functions and must be partially applied when used as an interceptor.
All interceptors must have the following signature: `(request: seleniumwire.request.Request) -> None`

For example, to use the remove_necessary_interceptor, use:
```python3
interceptor = functools.partial(
    interceptors.remove_necessary_interceptor,
    domain="example.com",
    data_path="./crawls/example.com/",
)
driver.request_interceptor = interceptor
```
"""


def remove_necessary_interceptor(request: seleniumwire.request.Request, domain: str, data_path: str) -> None:
    """
    Remove necessary cookies from a GET request.

    Args:
        request: A GET request.
        domain: Domain of the website.
        data_path: The path to store log files.
    """
    if request.headers.get("Cookie") is None:
        return

    cookie_header = CookieRequestHeader(request.headers["Cookie"], domain)
    cookie_header.remove_necessary()

    # Add to log file if cookie header is modified
    if cookie_header.get_header() != request.headers["Cookie"]:
        with open(data_path + "logs.txt", "a") as file:
            file.write(f"GET Request URL: {request.url}\n")
            file.write(f"Original Cookie Header: {request.headers['Cookie']}\n")
            file.write(f"Modified Cookie Header: {cookie_header.get_header()}\n\n")

    del request.headers["Cookie"]
    request.headers["Cookie"] = cookie_header.get_header()


def remove_all_interceptor(request: seleniumwire.request.Request) -> None:
    """
    Removes all cookies from a GET request.

    Args:
        request: A GET request.
    """
    if request.headers.get("Cookie") is None:
        return

    del request.headers["Cookie"]


def set_referer_interceptor(request: seleniumwire.request.Request, url: str, referer: Optional[str], data_path: str) -> None:
    """
    Spoof the referer header of a GET request to imitate a link click.

    If request.url matches url, then the referer header is modified to referer.

    Args:
        request: A GET request.
        url: The URL of the website being crawled.
        referer: The new referer value. If None, do nothing.
        data_path: The path to store log files.
    """
    if referer is None:
        return

    # TODO: Why do some websites not change the referer header?
    if URL(request.url) == URL(url):
        del request.headers["Referer"]
        request.headers["Referer"] = referer

        with open(data_path + "logs.txt", "a") as file:
            file.write(f"GET Request URL: {request.url}\n")
            file.write(f"Original Referer Header: {request.headers['Referer']}\n")
            file.write(f"Modified Referer Header: {referer}\n\n")