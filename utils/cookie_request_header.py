from utils.cookie_database import CookieDatabase, CookieClass


class CookieRequestHeader:
    """Related functions to parse and modify a cookie request header."""

    # Open Cookie Database has less unclassified cookies than Cookie-Script
    cookie_database = CookieDatabase.load_open_cookie_database()

    def __init__(self, cookie_header_value: str) -> None:
        """
        Args:
            cookie_header_value: The header value of a cookie request header.
        """
        self.cookies = {}

        raw_cookies = cookie_header_value.split("; ")
        for cookie in raw_cookies:
            key, value = cookie.split("=", 1)  # Split at first '=' (since value may contain '=')
            self.cookies[key] = value

    def remove_by_class(self, blacklist: tuple[CookieClass, ...]) -> None:
        """
        Remove all cookies with a class in blacklist from `self.cookies`.

        Args:
            blacklist: A tuple of cookie classes to remove.
        """
        for key in list(self.cookies.keys()):
            if CookieRequestHeader.cookie_database.get_cookie_class(key) in blacklist:
                del self.cookies[key]

    def get_header(self) -> str:
        """Return `self.cookies` as a cookie request header."""
        header = "; ".join(
            [str(key) + "=" + str(value) for key, value in self.cookies.items()]
        )

        return header
