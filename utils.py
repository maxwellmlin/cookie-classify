import tldextract

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


def get_domain_and_tld(url: str) -> str:
    """
    Return domain of `url`.

    A domain consists of the second-level domain and top-level domain. Removes "www." if exists.

    Args:
        url: URL to get the domain from.

    Returns:
        domain of `url`.
    """
    separated_url = tldextract.extract(url)
    domain = separated_url.domain
    suffix = separated_url.suffix

    # Check if "www" is part of the subdomain and remove it if present
    if domain.lower().startswith("www."):
        domain = domain[4:]

    return f"{domain}.{suffix}"
