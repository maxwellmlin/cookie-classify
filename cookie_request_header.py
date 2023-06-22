from cookiescript import CookieScript
from http.cookies import SimpleCookie
from urllib.parse import urlparse


class CookieRequestHeader:
    """
    See
    - https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cookie
    - https://docs.python.org/3/library/http.cookies.html
    """

    def __init__(self) -> None:
        self.cookiescript = CookieScript()

        self.cookies = None  # dictionary mapping cookies keys to values
        self.domain = None  # domain of cookie

    def load_header(self, cookie_header_value, url):
        """
        Load cookie request header as a dictionary.

        `cookie_header_value` should be the name-value pairs of a Cookie request header
        i.e., name=value; name2=value2; name3=value3

        `url` is the url of the cookie
        """

        cookies = SimpleCookie()
        cookies.load(cookie_header_value)

        # Transform morsels to dictionary
        cookies = {key: value.value for key, value in cookies.items()}

        self.cookies = cookies
        self.domain = urlparse(url).netloc  # TODO: Verify correctness

    def remove_necessary(self):
        """
        Remove all necessary cookies from self.cookies
        """

        necessary_removed = {}
        for key, value in cookies.items():
            if not self.cookiescript.get_cookie_class(self.domain, key) == 'Strictly Necessary':
                necessary_removed[key] = value

        self.cookies = necessary_removed

    def get_header(self):
        """
        Return the self.cookies dictionary as a cookies request header
        """

        header = "; ".join(
            [str(key) + "=" + str(value) for key, value in self.cookies.items()]
        )

        return header


if __name__ == "__main__":
    data = "MUID=0B2C44AA60C46BD30A4A579261D66A9E; MR=0"
    cookies = CookieRequestHeader()
    cookies.load_header(data, "google.com")

    print(cookies.get_header())
