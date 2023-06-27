import tldextract

# Utility functions for cookie-classify.


def get_domain(url: str) -> str:
    """
    Return domain of `url`.

    A domain consists of the second-level domain and top-level domain.

    Args:
        url (str): URL to get the domain from.

    Returns:
        str: domain of `url`.
    """
    separated_url = tldextract.extract(url)
    return f"{separated_url.domain}.{separated_url.suffix}"


def get_full_domain(url: str) -> str:
    """
    Return full domain of `url`.

    A full domain consists of the subdomain, second-level domain, and top-level domain.

    Args:
        url (str): URL to get the full domain from.

    Returns:
        str: full domain of `url`.
    """
    separated_url = tldextract.extract(url)
    full_domain = f"{separated_url.subdomain}.{separated_url.domain}.{separated_url.suffix}"

    # Remove leading '.' if subdomain is empty
    if full_domain[0] == ".":
        full_domain = full_domain[1:]

    return full_domain
