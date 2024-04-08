import tldextract
import logging
import os
import config
from pathlib import Path

# Utility functions for cookie-classify.


def get_domain(url: str) -> str:
    """
    Return domain of `url`.

    A domain consists of the second-level domain and top-level domain.

    Args:
        url: URL to get the domain from.

    Returns:
        domain of url.
    """
    separated_url = tldextract.extract(url)
    return f"{separated_url.domain}.{separated_url.suffix}"


def get_full_domain(url: str) -> str:
    """
    Return full domain of url.

    A full domain consists of the subdomain, second-level domain, and top-level domain.

    Args:
        url: URL to get the full domain from.

    Returns:
        full domain of url.
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
        logger.info(f"Calling '{func.__name__}' with args: {args}, kwargs: {kwargs}.")
        return func(*args, **kwargs)

    return wrapper


def get_directories(root: str) -> list[Path]:
    """
    Return a list of directories in a given root directory.

    Args:
        root: Path to the root directory.

    Returns:
        A list of directories.
    """
    p = Path(root)
    
    # List all directories in the path
    directories = [entry for entry in p.iterdir() if entry.is_dir()]
    return directories

def split(list: list, n: int):
    """
    Split list into n equally sized chunks.
    """
    k, m = divmod(len(list), n)
    return (list[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))