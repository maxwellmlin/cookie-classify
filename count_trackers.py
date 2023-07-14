import csv

def compare_trackers():
    paths_with_trackers = []
    
    no_trackers_after_reject = []

    # Read trackers_after_reject.csv
    with open('analysis/trackers_after_reject.csv', 'r') as file:
        csv_reader = csv.reader(file)
        next(csv_reader)
        
        for row in csv_reader:
            inner_site_path, length_detected_list = row
            if length_detected_list == '0':
                print("0 trackers detected after clicking reject all")
                break
    
    # Read trackers_in_normal.csv
    with open('analysis/trackers_in_normal.csv', 'r') as file:
        csv_reader = csv.reader(file)
        next(csv_reader)
        
        for row in csv_reader:
            inner_site_path, length_detected_list = row
            if length_detected_list == '0' and inner_site_path not in paths_with_trackers:
                paths_with_trackers.append(inner_site_path)
    
    # Print the paths with trackers
    for path in paths_with_trackers:
        print(path)
