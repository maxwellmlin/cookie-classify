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
            data_path: Path of the Open Cookie Databse CSV file.
            Defaults to "inputs/databases/open_cookie_database.csv".

        Returns:
            Classes from Open Cookie Database CSV as a dictionary.
            Lookup using `dict[cookie_key]`. `cookie_key` is the name of the cookie.
        """
        cookie_category_dict = {}

        with open(data_path, 'r') as file:
            csv_reader = csv.reader(file)

            next(csv_reader)

            for row in csv_reader:
                cookie_key = row[3]
                class_ = row[2]

                cookie_category_dict[cookie_key] = class_

        return cookie_category_dict

    def get_cookie_class(self, cookie_key: str) -> str:
        """
        Return the class of the given cookie.

        Args:
            cookie_key: Name of the cookie.

        Returns:
            The class of the cookie. Class can be either "Functional",
            "Preferences", "Analytics", or "Marketing".
        """
        if not (cookie_class := self.classes.get(cookie_key)):
            # cookie_key not in self.classes
            return "Unclassified"

        return cookie_class

    def is_necessary(self, cookie_key: str, **kwargs) -> bool:
        """
        Return whether the given cookie is necessary.

        For Open Cookie Database, "Functional" is equivalent to "Strictly Necessary".

        Args:
            cookie_key: Name of the cookie.

        Returns:
            Whether the given cookie is necessary.
        """
        return self.get_cookie_class(cookie_key) == "Functional"
