import tldextract

"""
Utility functions for cookie-classify.
"""


def get_domain(url):
    """
    Return domain of URL.

    `url` is the URL to get the domain from.
    """
    separated_url = tldextract.extract(url)
    return f"{separated_url.domain}.{separated_url.suffix}"
