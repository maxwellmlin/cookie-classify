from typing import Optional

import seleniumwire.request

from utils.cookie_request_header import CookieRequestHeader
from utils.url import URL
from utils.cookie_database import CookieClass

"""
Interceptors for seleniumwire.

Many of these functions are general functions and must be partially applied when used as an interceptor.
All interceptors must have the following signature: `(request: seleniumwire.request.Request) -> None`

For example, to use the remove_cookie_class_interceptor, use:
```python3
interceptor = functools.partial(
    interceptors.remove_cookie_class_interceptor,
    blacklist=blacklist,  # A tuple of cookie classes to remove
    data_path=data_path,  # The path to store log files
)
driver.request_interceptor = interceptor
```
"""


def remove_cookie_class_interceptor(request: seleniumwire.request.Request, blacklist: tuple[CookieClass, ...], data_path: str) -> None:
    """
    Remove cookies by class from a GET request.

    Args:
        request: A GET request.
        blacklist: A tuple of cookie classes to remove.
        data_path: The path to store log files.
    """
    if request.headers.get("Cookie") is None:
        return

    cookie_header = CookieRequestHeader(request.headers["Cookie"])
    cookie_header.remove_by_class(blacklist)

    old_header = request.headers["Cookie"]

    del request.headers["Cookie"]
    request.headers["Cookie"] = cookie_header.get_header()

    # Add to log file if cookie header is modified
    if cookie_header.get_header() != request.headers["Cookie"]:
        with open(data_path + "logs.txt", "a") as file:
            file.write(f"GET Request: {request.url}\n")
            file.write(f"Original Cookie Header: {old_header}\n")
            file.write(f"Modified Cookie Header: {request.headers['Cookie']}\n\n")


def remove_all_interceptor(request: seleniumwire.request.Request) -> None:
    """
    Removes all cookies from a GET request.

    Args:
        request: A GET request.
        data_path: The path to store log files.
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

    if URL(request.url) == URL(url):
        with open(data_path + "logs.txt", "a") as file:
            file.write(f"Injecting Referer Header: {referer}\n")

        del request.headers["Referer"]
        request.headers["Referer"] = referer
