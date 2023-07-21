import csv

def analyze_csv(csv_data):
    domain_trackers = {}
    for line in csv_data:
        # Extract the domain name from the path
        domain = line.split('/')[2]
        
        # Extract the number of trackers from the path
        trackers = int(line.split(',')[1])
        
        # Update the domain_trackers dictionary
        if domain in domain_trackers:
            domain_trackers[domain]["num_inner_pages"] += 1
            domain_trackers[domain]["total_trackers"] += trackers
        else:
            domain_trackers[domain] = {"num_inner_pages": 1, "total_trackers": trackers}
    
    return domain_trackers


# FIXME: Write this into a Jupyter notebook when VM storage becomes available
# for now just comment out each section to print results

# depth1_noquery_normal = "analysis/depth1_noquery_trackers_in_normal.csv"
# with open(depth1_noquery_normal, 'r') as file:
#     csv_data = file.readlines()

# depth1_noquery_normal_analysis = analyze_csv(csv_data)

# for domain, info in depth1_noquery_normal_analysis.items():
#     print(f"Domain: {domain}, Number of Inner Pages: {info['num_inner_pages']}, Total Trackers: {info['total_trackers']}")


depth1_noquery_reject = "analysis/depth1_noquery_after_reject.csv"
with open(depth1_noquery_reject, 'r') as file:
    csv_data = file.readlines()

depth1_noquery_reject_analysis = analyze_csv(csv_data)

for domain, info in depth1_noquery_reject_analysis.items():
    print(f"Domain: {domain}, Number of Inner Pages: {info['num_inner_pages']}, Total Trackers: {info['total_trackers']}")