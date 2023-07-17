import csv


def compare_trackers():
    no_trackers_after_reject = []  # List of inner site paths with trackers in normal crawl, but no trackers after rejection
    increased_trackers = []  # List of inner site paths with more trackers after rejection than in normal crawl
    never_trackers = []  # List of inner site paths with no trackers in either normal or rejection crawl
    violating_sites = []  # List of inner site paths with trackers in rejection

    with open('analysis/trackers_after_reject.csv', 'r') as reject_file, open('analysis/trackers_in_normal.csv', 'r') as normal_file:
        read_reject = csv.reader(reject_file)
        read_normal = csv.reader(normal_file)
        next(read_reject)
        next(read_normal)

        for row in read_normal:
            inner_site_path, length_detected_list = row
            length_detected_list_reject = get_length_detected_list(read_reject, inner_site_path)

            site_url = inner_site_path.replace('crawls/', '').replace('/0', '')

            if int(length_detected_list) > 0 and length_detected_list_reject == '0':  # if there are trackers in normal crawl, but not after reject
                no_trackers_after_reject.append(site_url)

            if int(length_detected_list) < int(length_detected_list_reject):  # if there are more trackers after reject than in normal crawl
                increased_trackers.append(site_url)

            if int(length_detected_list) == 0 and length_detected_list_reject == '0':  # if there are no trackers in either normal or reject
                never_trackers.append(site_url)

            if length_detected_list_reject != '0':  # if there are trackers in reject
                violating_sites.append(site_url)

    print("List of sites with no trackers after rejection:", len(no_trackers_after_reject), no_trackers_after_reject)
    print("List of sites with increased trackers after rejection:", len(increased_trackers), increased_trackers)
    print("List of sites that never contained trackers:", len(never_trackers), never_trackers)
    print("List of sites that violated GDPR:", len(violating_sites), violating_sites)


def get_length_detected_list(csv_reader, inner_site_path):
    for row in csv_reader:
        current_inner_site_path, length_detected_list = row
        if current_inner_site_path == inner_site_path:
            return length_detected_list

    return '0'  # If inner_site_path not found, return '0'


# Call the function to compare the trackers
compare_trackers()
