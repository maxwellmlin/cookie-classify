from urllib.parse import urlparse, unquote_plus
import utils


class URL(object):
    """A URL object that can be compared with other URL objects."""

    def __init__(self, url):
        self.url = url  # Original URL

        parts = urlparse(url)

        # NOTE: We assume the same webpage is served regardless of
        # scheme, params, query, and fragment
        self.parts_to_compare = parts._replace(
            scheme="",
            netloc=parts.hostname,  # removes port, username, and password
            path=unquote_plus(parts.path),  # replaces %xx escapes and plus signs
            params="",
            query="",  # TODO: is query important?
            fragment=""
        )

    def domain(self):
        """
        Return domain of URL.

        Returns:
            Domain of `self.url`.
        """
        return utils.get_domain(self.url)

    def __eq__(self, other):
        return self.parts_to_compare == other.parts_to_compare

    def __hash__(self):
        return hash(self.parts_to_compare)


if __name__ == "__main__":
    url1 = URL("https://www.google.com:123/El+Ni%C3%B1o/hi?q=hello+world#fragment")
    url2 = URL("http://www.google.com/El Niño/hi")
    foo = {}
    foo[url1] = 'url1'
    foo[url2] = 'url2'
    print(foo[url1])
