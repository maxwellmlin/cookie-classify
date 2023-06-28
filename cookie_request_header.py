from cookiescript import CookieScript


class CookieRequestHeader:
    """Related functions to parse and modify a cookie request header."""

    cookie_database = CookieScript() # FIXME: change to opencookieDB

    def __init__(self, cookie_header_value: str, domain: str) -> None:
        """
        Args:
            cookie_header_value (str): The header value of a cookie request header.
            domain (str): The domain of the website.
        """
        self.cookies = {}

        raw_cookies = cookie_header_value.split("; ")
        for cookie in raw_cookies:
            key, value = cookie.split("=", 1)  # Split at first '=' (since value may contain '=')
            self.cookies[key] = value

        self.domain = domain

    def remove_necessary(self) -> None:
        """Remove all necessary cookies from `self.cookies`."""
        necessary_removed = {}
        for key, value in self.cookies.items():
            if not CookieRequestHeader.cookie_database.is_necessary(key, self.domain):
                necessary_removed[key] = value

        self.cookies = necessary_removed

    def get_header(self) -> str:
        """Return `self.cookies` as a cookie request header."""
        header = "; ".join(
            [str(key) + "=" + str(value) for key, value in self.cookies.items()]
        )

        return header

    def __ne__(self, __value: object) -> bool:
        return self.get_header() != __value

    def __str__(self) -> str:
        return self.get_header()
