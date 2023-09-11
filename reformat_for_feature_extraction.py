## IGNORE THIS FILE FOR NOW 
## in case we want to train a model on the same set of cookies we want to classify for in-sample testing

import json
import os
import utils

def get_directories(root: str) -> list[str]:
    """
    Return a list of directories in a given root directory.

    Args:
        root: Path to the root directory.

    Returns:
        A list of directories.
    """
    dirs = []
    for item in os.listdir(root):
        path = os.path.join(root, item)
        if os.path.isdir(path):
            dirs.append(path)

    return dirs

def get_response_cookies(file: str) -> list[dict[str, str, str]]:
    """
    Returns a list of cookies from response entries in an HAR file.
    [HAR Specification](http://www.softwareishard.com/blog/har-12-spec/).

    Args:
        file: Path to the HAR file.
    Returns:
        A list of dictionaries representing all cookies in HTTP responses in that HAR file.
    """

    cookies = []
    data = json.load(open(file, "r")) # parses JSON data into Python dictionary
    for entry in data["log"]["entries"]: # each entry is an HTTP request/response pair
        
        response = entry["response"] # extract response dictionary

        if response.get("cookies"): # response contains cookies
            for cookie in response["cookies"]:
                # print(cookie)
                if cookie.get("domain"): # if cookie has domain
                    cookies.append({"Cookie Name": cookie["name"], "Cookie Value": cookie["value"], "Cookie Domain": cookie["domain"]})

    return cookies

def get_request_cookies(file: str) -> list[dict[str, str, str]]:
    """
    Returns a list of cookies from request entries in an HAR file.
    [HAR Specification](http://www.softwareishard.com/blog/har-12-spec/).

    Args:
        file: Path to the HAR file.
    Returns:
        A list of dictionaries representing all cookies in HTTP requests in that HAR file.
    """

    cookies = []
    data = json.load(open(file, "r")) # parses JSON data into Python dictionary
    for entry in data["log"]["entries"]: # each entry is an HTTP request/response pair
        
        response = entry["request"] # extract response dictionary

        if response.get("cookies"): # response contains cookies
            for cookie in response["cookies"]:
                # print(cookie)
                if cookie.get("domain"): # if cookie has domain
                    cookies.append({"Cookie Name": cookie["name"], "Cookie Value": cookie["value"], "Cookie Domain": cookie["domain"]})

    return cookies

def merge_cookies(detected_list_from_responses: list[dict[str, str, str]], file: str) -> list[dict[str, str, str]]:
    """
    Returns a list of cookies from request entries in an HAR file that also appeared in a response entry.

    Args:
        detected_list_from_responses: List of cookies from response entries in an HAR file.
        file: Path to the HAR file.

    Returns:
        A list of dictionaries representing all cookies in HTTP requests in that HAR file.
    """

    detected_list_from_requests = []
    data = json.load(open(file, "r")) # parses JSON data into Python dictionary
    for entry in data["log"]["entries"]: # each entry is an HTTP request/response pair
        
        request = entry["request"] # extract request dictionary

        for cookie in request.get("cookies"):
            cookie_names = [d["Cookie Name"] for d in detected_list_from_responses]
            if cookie.get("name") in cookie_names: # if cookie name is in list of detected cookies from responses
                detected_list_from_requests.append({"Cookie Name": cookie["name"], "Cookie Value": cookie["value"]})
                # detected_list_from_requests.append(cookie)

    return detected_list_from_requests

def main():
    pass

if __name__ == "__main__":
    main()