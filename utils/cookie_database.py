from __future__ import annotations

from enum import Enum
import json
import csv

"""
Lookup a cookie's CookieClass by its key (name).
"""

class CookieClass(Enum):
    """
    Corresponds to the ICC cookie categories

    See: https://www.cookielaw.org/wp-content/uploads/2019/12/icc_uk_cookiesguide_revnov.pdf
    """

    STRICTLY_NECESSARY = "Strictly Necessary"
    PERFORMANCE = "Performance"
    FUNCTIONALITY = "Functionality"
    TARGETING = "Targeting"
    UNCLASSIFIED = "Unclassified"


class CookieDatabase:
    """Load a database to lookup cookie class by key."""

    def __init__(self, classes: dict[str, CookieClass]) -> None:
        """
        Args:
            classes: Dictionary mapping cookie keys to cookie classes.
        """
        self.classes = classes

    @classmethod
    def load_cookie_script(cls, data_path="inputs/databases/cookie_script.json") -> CookieDatabase:
        """
        Initialize CookieDatabase using Cookie-Script JSON file.

        Args:
            cookie_script_path: Path of the Cookie-Script JSON file.
            Defaults to "inputs/databases/cookie_script.json".

        Returns:
            CookieDatabase object containing classes from Cookie-Script.
        """
        cookie_script_to_enum = {
            "Strictly Necessary": CookieClass.STRICTLY_NECESSARY,
            "Performance": CookieClass.PERFORMANCE,
            "Functionality": CookieClass.FUNCTIONALITY,
            "Targeting": CookieClass.TARGETING,
            "Unclassified": CookieClass.UNCLASSIFIED
        }

        object_list = []
        with open(data_path) as file:
            for line in file:
                object_ = json.loads(line)
                object_list.append(object_)

        classes = {}
        for object_ in object_list:
            cookies = object_["cookies"]

            for cookie in cookies:
                cookie_key = cookie.pop("cookieKey")
                classes[cookie_key] = cookie_script_to_enum[cookie["class"]]

        return cls(classes)

    @classmethod
    def load_open_cookie_database(cls, data_path="inputs/databases/open_cookie_database.csv") -> CookieDatabase:
        """
        Initialize CookieDatabase using Open Cookie Database CSV file.
        See: https://github.com/jkwakman/Open-Cookie-Database

        Args:
            data_path: Path of the Open Cookie Database CSV file.
            Defaults to "inputs/databases/open_cookie_database.csv".

        Returns:
            CookieDatabase object containing classes from Open Cookie Database.
        """
        open_cookie_database_to_enum = {
            "Functional": CookieClass.STRICTLY_NECESSARY,
            "Preferences": CookieClass.FUNCTIONALITY,
            "Analytics": CookieClass.PERFORMANCE,
            "Marketing": CookieClass.TARGETING
        }

        classes = {}
        with open(data_path, 'r') as file:
            csv_reader = csv.reader(file)

            next(csv_reader)  # skip header

            for row in csv_reader:
                cookie_key = row[3]
                class_ = row[2]

                classes[cookie_key] = open_cookie_database_to_enum[class_]

        return cls(classes)

    def get_cookie_class(self, cookie_key: str) -> CookieClass:
        """
        Return the class of the given cookie.

        Args:
            cookie_key: Name of the cookie.
        Returns:
            The class of the cookie.
        """
        # NOTE: no differentiation is made between unknown (not in database)
        # and unclassified (in database, but category unknown) cookies
        if cookie_key not in self.classes:
            return CookieClass.UNCLASSIFIED

        return self.classes[cookie_key]
