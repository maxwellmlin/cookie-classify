import csv


class OpenCookieDatabase:
    """Related functions for Open Cookie Database lookup."""

    def __init__(self) -> None:
        self.classes = self.load_database()

    @staticmethod
    def load_database(data_path="inputs/databases/open_cookie_database.csv") -> dict[str, str]:
        """
        Load classes from Open Cookie Database CSV file as a dictionary.

        Args:
            data_path (str, optional): Path of the Open Cookie Databse CSV file.
            Defaults to "inputs/databases/open_cookie_database.csv".

        Returns:
            dict[str, str]: Classes from Open Cookie Database CSV as a dictionary.
            Lookup using `dict[cookie_key]`.
            `cookie_key` is the name of the cookie.
        """
        cookie_category_dict = {}

        with open(data_path, 'r') as file:
            csv_reader = csv.reader(file)

            # CSV lines are in the format:
            # "ID,Platform,Category,Cookie / Data Key name,Domain,Description,Retention period,Data Controller,User Privacy & GDPR Rights Portals,Wildcard match"
            next(csv_reader)

            for row in csv_reader:
                cookie_key = row[3]
                category = row[2]

                cookie_category_dict[cookie_key] = category

        return cookie_category_dict

    def get_cookie_class(self, cookie_key: str) -> str:
        """
        Return the class of the given cookie.

        Args:
            cookie_key (str): Name of the cookie.

        Returns:
            str: The class of the cookie. Class can be either "Functional",
            "Preferences", "Analytics", or "Marketing".
        """
        if not (cookie_class := self.classes.get(cookie_key)):
            # cookie_key not in cookie_category_dict
            return "Unclassified"

        return cookie_class

    def is_necessary(self, cookie_key: str, *args) -> bool:
        """
        Return whether the given cookie is Functional (equivalent to Strictly Necessary).

        Args:
            cookie_key (str): Name of the cookie.

        Returns:
            bool: Whether the given cookie is Functional.
        """
        return self.get_cookie_class(cookie_key) == "Functional"
