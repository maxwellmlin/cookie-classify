from typing import Optional

import seleniumwire.request

from utils.cookie_request_header import CookieRequestHeader
from utils.url import URL
from utils import utils
from utils.cookie_database import CookieClass

"""
Interceptors for seleniumwire.

Many of these functions are general functions and must be partially applied when used as an interceptor.
All interceptors must have the following signature: (request: seleniumwire.request.Request) -> None

For example, to use the remove_cookie_class_interceptor, use:
interceptor = functools.partial(
    interceptors.remove_cookie_class_interceptor,
    blacklist=blacklist,
)
driver.request_interceptor = interceptor
"""


def remove_cookie_class_interceptor(request: seleniumwire.request.Request, blacklist: tuple[CookieClass, ...]) -> None:
    """
    Remove cookies by class from a request.

    Args:
        request: The request to modify.
        blacklist: A tuple of cookie classes to remove.
    """
    if request.headers.get("Cookie") is None:
        return

    cookie_header = CookieRequestHeader(request.headers["Cookie"])
    cookie_header.remove_by_class(blacklist)

    del request.headers["Cookie"]
    request.headers["Cookie"] = cookie_header.get_header()


def remove_third_party_interceptor(request: seleniumwire.request.Request, current_url: str) -> None:
    """
    Remove all third-party cookies from a request.

    A third-party cookie is a cookie that is not from the current website being crawled.

    Args:
        request: The request to modify.
        current_url: The URL of the website currently being crawled.
    """
    if request.headers.get("Cookie") is None:
        return

    if utils.get_domain(request.url) != utils.get_domain(current_url):
        del request.headers["Cookie"]


def remove_all_interceptor(request: seleniumwire.request.Request) -> None:
    """
    Removes all cookies from a request.

    Args:
        request: The request to modify.
    """
    if request.headers.get("Cookie") is None:
        return

    del request.headers["Cookie"]


def set_referer_interceptor(request: seleniumwire.request.Request, url: str, referer: Optional[str]) -> None:
    """
    Spoof the referer header of a request to imitate a link click.

    If request.url matches url, then the referer header is modified to referer.

    Args:
        request: The request to modify.
        url: The URL of the website currently being crawled.
        referer: The new referer value. If None, do nothing.
    """
    if referer is None:
        return

    # The exact URL must be matched, so that the referer is only
    # spoofed for the immediate website (not any external resources).
    if URL(request.url) == URL(url):
        del request.headers["Referer"]
        request.headers["Referer"] = referer
