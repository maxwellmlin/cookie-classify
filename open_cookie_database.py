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
            dict[str, str]: Classes from Cookie-Script JSON file as a dictionary.
            Lookup using `dict[cookie_key]`.
            `cookie_key` is the name of the cookie.
        """
        pass

    def get_cookie_class(self, cookie_key: str) -> str:
        """
        Return the class of the given cookie.

        Args:
            cookie_key (str): Name of the cookie.

        Returns:
            str: The class of the cookie. Class can be either "Functional",
            "Preferences", "Analytics", or "Marketing".
        """

    def is_necessary(self, cookie_key: str, domain: str) -> bool:
        """
        Return whether the given cookie is Strictly Necessary.

        Args:
            cookie_key (str): Name of the cookie.
            domain (str): Domain of the website.

        Returns:
            bool: Whether the given cookie is Strictly Necessary.
        """
