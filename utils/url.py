from urllib.parse import urlparse, unquote_plus
import utils.utils as utils


class URL():
    """A URL object that can be compared with other URL objects."""

    def __init__(self, url):
        self.url = url  # Original URL

        parts = urlparse(url)

        # NOTE: Only compare hostname and path
        self.parts_to_compare = parts._replace(
            scheme="",
            netloc=parts.hostname,  # removes port, username, and password
            path=unquote_plus(parts.path),  # replaces %xx escapes and plus signs
            params="",
            query="",
            fragment=""
        )

    def domain(self):
        """
        Return domain of URL.

        Returns:
            Domain of self.url
        """
        return utils.get_domain(self.url)

    def __eq__(self, other):
        return self.parts_to_compare == other.parts_to_compare

    def __hash__(self):
        return hash(self.parts_to_compare)
