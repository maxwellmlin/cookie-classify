import seleniumwire.request

from cookie_request_header import CookieRequestHeader

"""
Interceptors for seleniumwire.

NOTE: Many of these functions are general functions and must be partially applied when used as an interceptor.
All interceptors must have the following signature: (request: seleniumwire.request.Request) -> None

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
    if cookie_header != request.headers["Cookie"]:
        with open(data_path + "logs.txt", "a") as file:
            file.write(f"GET Request URL: {request.url}\n")
            file.write(f"Original Cookie Header: {request.headers['Cookie']}\n")
            file.write(f"Modified Cookie Header: {cookie_header}\n\n")

    request.headers["Cookie"] = cookie_header


def remove_all_interceptor(request: seleniumwire.request.Request) -> None:
    """
    Removes all cookies from a GET request.

    Args:
        request: A GET request.
    """
    if request.headers.get("Cookie") is None:
        return

    del request.headers["Cookie"]


def passthrough_interceptor(request: seleniumwire.request.Request) -> None:
    """
    Do nothing to a GET request.

    Args:
        request: A GET request.
    """


def set_referer_interceptor(request: seleniumwire.request.Request, referer) -> None:
    """
    Set the referer header of a GET request.

    Args:
        request: A GET request.
        referer: The new referer value.
    """
    request.headers["Referer"] = referer
