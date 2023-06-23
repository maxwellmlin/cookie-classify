import json


class CookieScript:
    """
    Related functions for CookieScript database lookup.
    """

    def __init__(self) -> None:
        self.cookiescript = self.load_cookie_script()

    def load_cookie_script(self, cookie_script_path="inputs/databases/cookiescript.json"):
        """
        Load Cookie-Script JSON file as a dictionary.

        `cookie_script_path` is the path of the Cookie-Script JSON file.

        To obtain a cookie from the dictionary, use:
        cookie_data = cookiescript[domain][cookie_key]
        """

        object_list = []
        with open(cookie_script_path) as file:
            for line in file:
                object_ = json.loads(line)
                object_list.append(object_)

        cookiescript = {}

        for object_ in object_list:
            # Extract the domain and cookies from the current JSON object
            domain = object_["website"]
            cookies = object_["cookies"]

            # Create a nested dictionary for the current website
            cookiescript[domain] = {}

            # Populate the nested dictionary with cookie data for the current website
            for cookie in cookies:
                cookie_key = cookie.pop("cookieKey")
                cookiescript[domain][cookie_key] = cookie

        return cookiescript

    def get_cookie_class(self, domain, cookie_key):
        """
        Return the class of the given cookie.

        `domain` is the 2nd-level and top-level domain (e.g., 'google.com')
        `cookie_key` is the name of the cookie

        The class will be one of the following strings:
        - "Strictly Necessary"
        - "Performance"
        - "Functionality"
        - "Targeting"
        - "Unclassified"
        """

        if not (domain_cookies := self.cookiescript.get(domain)):
            # domain not in cookie_script
            return "Unclassified"

        if not (cookie := domain_cookies.get(cookie_key)):
            # cookie_key not in cookie_script
            return "Unclassified"

        return cookie["class"]

    def is_necessary(self, domain, cookie_key):
        """
        Return whether the given cookie is Strictly Necessary.

        `domain` is the 2nd-level and top-level domain (e.g., 'google.com')
        `cookie_key` is the name of the cookie
        """

        return self.get_cookie_class(domain, cookie_key) == "Strictly Necessary"


if __name__ == "__main__":
    print("checking for duplicates...")
    cs = CookieScript()
