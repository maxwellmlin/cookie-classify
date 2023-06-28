import json


class CookieScript:
    """Related functions for CookieScript database lookup."""

    def __init__(self) -> None:
        self.classes = self.load_cookie_script()

    @staticmethod
    def load_cookie_script(cookie_script_path="inputs/databases/cookiescript.json") -> dict[str, dict[str, str]]:
        """
        Load classes from Cookie-Script JSON file as a dictionary.

        Args:
            cookie_script_path (str, optional): Path of the Cookie-Script JSON file.
            Defaults to "inputs/databases/cookiescript.json".

        Returns:
            dict[str, dict[str, str]]: Classes from Cookie-Script JSON file as a dictionary.
            Lookup using `dict[domain][cookie_key]`.
            `domain` is the domain of the website.
            `cookie_key` is the name of the cookie.
        """
        object_list = []
        with open(cookie_script_path) as file:
            for line in file:
                object_ = json.loads(line)
                object_list.append(object_)

        classes = {}

        for object_ in object_list:
            # Extract the domain and cookies from the current JSON object
            domain = object_["website"]
            cookies = object_["cookies"]

            # Create a nested dictionary for the current website
            classes[domain] = {}

            # Populate the nested dictionary with the cookie class for the current website
            for cookie in cookies:
                cookie_key = cookie.pop("cookieKey")
                classes[domain][cookie_key] = cookie["class"]

        return classes

    def get_cookie_class(self, domain: str, cookie_key: str) -> str:
        """
        Return the class of the given cookie.

        Args:
            domain (str): Domain of the website.
            cookie_key (str): Name of the cookie.

        Returns:
            str: The class of the cookie. Class can be either "Strictly Necessary",
            "Performance", "Functionality", "Targeting", or "Unclassified".
        """
        if not (domain_cookies := self.classes.get(domain)):
            # domain not in cookie_script
            return "Unclassified"

        if not (cookie_class := domain_cookies.get(cookie_key)):
            # cookie_key not in cookie_script
            return "Unclassified"

        return cookie_class

    def is_necessary(self, cookie_key: str, domain: str) -> bool:
        """
        Return whether the given cookie is Strictly Necessary.

        Args:
            cookie_key (str): Name of the cookie.
            domain (str): Domain of the website.

        Returns:
            bool: Whether the given cookie is Strictly Necessary.
        """
        return self.get_cookie_class(domain, cookie_key) == "Strictly Necessary"
