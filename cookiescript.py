import json


class CookieScript:
    def __init__(self) -> None:
        self.cookiescript = self.load_cookie_script()

    def load_cookie_script(self, cookie_script_path="inputs/cookiescript.json"):
        """
        Returns Cookie-Script JSON file as a dictionary.

        The JSON file is reformatted as relevant key-value pairs.
        i.e., cookie_data = cookie_script[site_url][cookie_name]
        """
        object_list = []
        with open(cookie_script_path) as file:
            for line in file:
                object_ = json.loads(line)
                object_list.append(object_)

        cookiescript = {}

        for object_ in object_list:
            # Extract the website and cookies from the current JSON object
            website = object_["website"]
            cookies = object_["cookies"]

            # Create a nested dictionary for the current website
            cookiescript[website] = {}

            # Populate the nested dictionary with cookie data for the current website
            for cookie in cookies:
                cookie_key = cookie.pop(
                    "cookieKey"
                )  # Remove 'cookieKey' from the dictionary values and assign it as a key
                cookiescript[website][cookie_key] = cookie

        return cookiescript
