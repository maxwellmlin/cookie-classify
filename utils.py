import tldextract
import config
import logging

# Utility functions for cookie-classify.


def get_domain(url: str) -> str:
    """
    Return domain of `url`.

    A domain consists of the second-level domain and top-level domain.

    Args:
        url: URL to get the domain from.

    Returns:
        domain of `url`.
    """
    separated_url = tldextract.extract(url)
    return f"{separated_url.domain}.{separated_url.suffix}"


def get_full_domain(url: str) -> str:
    """
    Return full domain of `url`.

    A full domain consists of the subdomain, second-level domain, and top-level domain.

    Args:
        url: URL to get the full domain from.

    Returns:
        full domain of `url`.
    """
    separated_url = tldextract.extract(url)

    if separated_url.subdomain == "":
        return get_domain(url)

    return f"{separated_url.subdomain}.{separated_url.domain}.{separated_url.suffix}"


def log(func):
    """
    Decorator for logging function calls.
    """
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(config.LOGGER_NAME)
        logger.debug(f"Calling `{func.__name__}` with args: {args}, kwargs: {kwargs}")
        return func(*args, **kwargs)

    return wrapper
