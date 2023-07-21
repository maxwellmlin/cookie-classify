import json
import os
import utils
import csv

if not os.path.exists("analysis"):
    os.mkdir("analysis")


def detect_tracking(blocklist, url_list):
    """
    Check if any URLs from a list appear in a blocklist of known tracking cookies.

    Args:
        blocklist: Set of blocked domains.
        url_list: List of URLs.

    Returns:
        A list of detected trackers.
    """

    detected_trackers = []
    for url in url_list:
        if utils.get_full_domain(url) in blocklist:
            detected_trackers.append(url)

    return detected_trackers


def get_urls_from_har(file: str) -> list[str]:
    """
    Returns a list of cookies from an HAR file.
    [HAR Specification](http://www.softwareishard.com/blog/har-12-spec/).

    Args:
        file: Path to the HAR file.
    Returns:
        A list of cookies.
    """

    all_urls = []
    data = json.load(open(file, "r"))
    for entry in data["log"]["entries"]:
        request = entry["request"]

        if (url := request.get("url")) and request.get("cookies"):
            all_urls.append(url)

    return all_urls


def get_tracking_sites(list_path: str = "inputs/blocklists/") -> set[str]:
    """
    Get tracking sites from blocklists.

    Args:
        list_path: Path to blocklists. Defaults to "inputs/blocklists/".

    Returns:
        A set of tracking sites.
    """
    lists = []
    for item in os.listdir(list_path):
        path = os.path.join(list_path, item)
        lists.append(path)

    tracking_sites = set()
    for list_path in lists:
        with open(list_path) as file:
            lines = file.readlines()
            for line in lines:
                tracking_sites.add(line.rstrip())

    # print("Tracking sites aggregated from 4 blocklists.")
    return tracking_sites


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


# Create set of tracking sites from aggregation of 4 blocklists
trackings_sites = get_tracking_sites()


def analyze_har(har_path: str):
    """
    Return a list of tracking cookies detected in the specified HAR file.

    Args:
        har_path: Path to the HAR file.

    Returns:
        A list of detected tracking cookies.
    """
    urls = get_urls_from_har(har_path)
    detected_list = detect_tracking(trackings_sites, urls)
    return detected_list

success_file_path = "inputs/sites/success.txt"
with open(success_file_path, "r") as success_file:
    success_lines = success_file.readlines()

domain_paths = get_directories("crawls/depth1_noquery")
incomplete_runs = 0
total_runs = 0
for site in domain_paths:
    # Skip if site is not in success.txt
    # if not any(site in line for line in success_lines):
    #     continue

    inner_site_paths = get_directories(site)
    total_runs += len(inner_site_paths)

    for inner_site_path in inner_site_paths:
        normal_har_path = f"{inner_site_path}/normal.json"
        intercept_har_path = f"{inner_site_path}/after_reject.json"

        if not os.path.isfile(normal_har_path) or not os.path.isfile(intercept_har_path):
            # Requires both normal and intercept HAR files to exist
            incomplete_runs += 1
            continue

        detected_list_normal = analyze_har(normal_har_path)

        # Create file if it doesn't exist; if it exists then write a row for each inner site path with a count of the number of trackers.
        normal_file = "analysis/depth1_noquery_trackers_in_normal.csv"
        normal_file_exists = os.path.isfile(normal_file)

        with open(normal_file, mode="a", newline="") as file1:
            writer = csv.writer(file1)

            if not normal_file_exists:
                writer.writerow(["Inner Site Path", "Length of Detected List"])

            writer.writerow([inner_site_path, len(detected_list_normal)])
            file1.flush()

        # Repeat for files generated after run with intercept.
        detected_list_intercept = analyze_har(intercept_har_path)

        intercept_file = "analysis/depth1_noquery_after_reject.csv"
        intercept_file_exists = os.path.isfile(intercept_file)

        with open(intercept_file, mode="a", newline="") as file2:
            writer = csv.writer(file2)

            if not intercept_file_exists:
                writer.writerow(["Inner Site Path", "Length of Detected List"])

            writer.writerow([inner_site_path, len(detected_list_intercept)])
            file2.flush()

print("Total inner pages:", total_runs)
print("Incomplete inner pages:", incomplete_runs)