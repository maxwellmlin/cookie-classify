from cookiescript import CookieScript
from http.cookies import SimpleCookie
# from urllib.parse import urlparse  # TODO: Do we need this?


class CookieRequestHeader:
    """
    Related functions to parse and modify a cookie request header.

    See
    - https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cookie
    - https://docs.python.org/3/library/http.cookies.html
    """

    cookiescript = CookieScript()

    def __init__(self, domain, cookie_header_value) -> None:
        """
        Load cookie request header as a dictionary.

        `domain` is the domain of the cookie

        `cookie_header_value` should be the name-value pairs of a cookie request header
        e.g., 'name=value; name2=value2; name3=value3'
        """

        cookies = SimpleCookie()
        cookies.load(cookie_header_value)

        self.cookies = {key: value.value for key, value in cookies.items()}
        # self.domain = urlparse(domain).netloc  # TODO: Do we need this?
        self.domain = domain

    def remove_necessary(self):
        """
        Remove all necessary cookies from self.cookies.
        """

        necessary_removed = {}
        for key, value in self.cookies.items():
            if not CookieRequestHeader.cookiescript.is_necessary(self.domain, key):
                necessary_removed[key] = value

        self.cookies = necessary_removed

    def get_header(self):
        """
        Return the self.cookies dictionary as a cookie request header.
        """

        header = "; ".join(
            [str(key) + "=" + str(value) for key, value in self.cookies.items()]
        )

        return header


if __name__ == "__main__":
    # Test code
    data = "MUID=0B2C44AA60C46BD30A4A579261D66A9E; MR=0; _dc_gtm_UA-54090495-1=necessary; hi=bye"
    cookies = CookieRequestHeader("google.com", data)
    cookies.remove_necessary()

    print(cookies.get_header())
