from urllib.parse import urlparse, unquote_plus


class URL(object):
    """A URL object that can be compared with other URL objects."""

    def __init__(self, url):
        self.url = url  # Original URL

        parts = urlparse(url)

        # Parts to compare
        # NOTE: We assume the same webpage is served regardless of
        # scheme, params, query, and fragment
        self.parts = parts._replace(
            scheme="",
            netloc=parts.hostname,  # removes port, username, and password
            path=unquote_plus(parts.path),  # replaces %xx escapes and plus signs
            params="",
            query="",  # TODO: is query important?
            fragment=""
        )

    def __eq__(self, other):
        return self.parts == other.parts

    def __hash__(self):
        return hash(self.parts)

    def __str__(self) -> str:
        return self.url


if __name__ == "__main__":
    url1 = URL("https://www.google.com:123/El+Ni%C3%B1o/hi?q=hello+world#fragment")
    url2 = URL("http://www.google.com/El Niño/hi")
    print(url1 == url2)
