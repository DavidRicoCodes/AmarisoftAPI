import re
import csv

# Fix regex patterns
phy_pattern = re.compile(r"\[PHY\].*?mcs=(\d+)")
ip_pattern = re.compile(r"\[IP\] .*? (\d+\.\d+\.\d+\.\d+):(\d+) > (\d+\.\d+\.\d+\.\d+):(\d+)")

def parse_amarisoft_log(log_file, output_csv):
    last_mcs = None
    parsed_data = []
    
    with open(log_file, 'r', encoding='utf-8') as file:
        for line in file:
            # Capture the last seen MCS value
            phy_match = phy_pattern.search(line)
            if phy_match:
                print("match")
                last_mcs = int(phy_match.group(1))
                continue
            
            # Capture IP packet data
            ip_match = ip_pattern.search(line)
            if ip_match:
                src_ip, src_port, dst_ip, dst_port = ip_match.groups()
                parsed_data.append([src_ip, src_port, dst_ip, dst_port, last_mcs])

    # Save extracted data to CSV
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Source IP", "Source Port", "Destination IP", "Destination Port", "MCS"])
        writer.writerows(parsed_data)

# Usage
log_filename = "OUTPUT/ue0.log"  # Change to your log filename
output_filename = "parsed_data.csv"  
parse_amarisoft_log(log_filename, output_filename)

print(f"Data extracted and saved to {output_filename}")
