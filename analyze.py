import json
import os
import utils


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
    [HAR Specificication](http://www.softwareishard.com/blog/har-12-spec/).

    Args:
        file: Path to the HAR file.
    Returns:
        A list of cookies.
    """

    all_urls = []
    data = json.load(open(file, 'r'))
    for entry in data['log']['entries']:
        request = entry['request']
        
        if url := request.get('url'):
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

    return tracking_sites


# Create set of tracking sites from aggregation of 4 blocklists
trackings_sites = get_tracking_sites()

# TODO: run crawl with tracking/targeting cookies removed, then analyze HAR files to see which (if any) tracking cookies remain
urls = get_urls_from_har("crawls/myflixer.to/0/normal.json")

parsed_json = detect_tracking(trackings_sites, urls)
print(parsed_json)
print(len(parsed_json))