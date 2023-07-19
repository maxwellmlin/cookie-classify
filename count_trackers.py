import csv


def compare_trackers():
    no_trackers_after_reject = []  # List of inner site paths with trackers in normal crawl, but no trackers after rejection
    increased_trackers = []  # List of inner site paths with more trackers after rejection than in normal crawl
    never_trackers = []  # List of inner site paths with no trackers in either normal or rejection crawl
    violating_sites = []  # List of inner site paths with trackers after we click the reject button

    with open('analysis/depth1_trackers_after_reject.csv', 'r') as reject_file, open('analysis/depth1_trackers_in_normal.csv', 'r') as normal_file:
        read_reject = csv.reader(reject_file)
        read_normal = csv.reader(normal_file)

        # Skip header
        next(read_reject)
        next(read_normal)

        length = 0

        # Since both csvs are sorted by inner site path, we can just iterate through both at the same time
        for normal, after_reject in zip(read_normal, read_reject):
            inner_site_path, num_trackers_normal = normal
            _, num_trackers_reject = after_reject

            if inner_site_path != _:
                raise RuntimeError("Inner site paths do not match")

            num_trackers_normal = int(num_trackers_normal)
            num_trackers_reject = int(num_trackers_reject)

            # length_detected_list_reject = get_length_detected_list(read_reject, inner_site_path)

            site_url = inner_site_path.replace('crawls/', '').replace('/0', '')

            if num_trackers_normal > 0 and num_trackers_reject == 0:  # if there are trackers in normal crawl, but not after reject
                no_trackers_after_reject.append(site_url)

            if num_trackers_normal < num_trackers_reject:  # if there are more trackers after reject than in normal crawl
                increased_trackers.append(site_url)

            if num_trackers_normal == 0 and num_trackers_reject == 0:  # if there are no trackers in either normal or reject
                never_trackers.append(site_url)

            if num_trackers_reject != 0:  # if there are trackers in reject
                violating_sites.append(site_url)

            length += 1

    print("Total sites:", length)
    print("List of sites with no trackers after rejection:", len(no_trackers_after_reject))
    print("List of sites with increased trackers after rejection:", len(increased_trackers))
    print("List of sites that never contained trackers:", len(never_trackers))
    print("List of sites that violated GDPR:", len(violating_sites))


def get_length_detected_list(csv_reader, inner_site_path):
    for row in csv_reader:
        current_inner_site_path, length_detected_list = row
        if current_inner_site_path == inner_site_path:
            return length_detected_list

    return '0'  # If inner_site_path not found, return '0'


# Call the function to compare the trackers
compare_trackers()
