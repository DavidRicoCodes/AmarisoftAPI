import re
import csv
import sys
import os
from datetime import datetime

if len(sys.argv) < 2:
    print("Usage: python3 parser.py <output_dir>")
    sys.exit(1)

# Pattern to capture the MCS value (lines containing "mcs=NUM")
mcs_line_pattern = re.compile(r"^\s*mcs=(\d+)", re.IGNORECASE)

# Pattern to capture the IP line with timestamp (assumed format HH:MM:SS.mmm)
ip_line_pattern = re.compile(
    r"^(\d{2}:\d{2}:\d{2}\.\d{3}).*\[IP\].*? (\d+\.\d+\.\d+\.\d+):(\d+) > (\d+\.\d+\.\d+\.\d+):(\d+)"
)

# Pattern to identify hex dump lines (lines starting with an offset, e.g., "0000:")
hex_line_pattern = re.compile(r"^\s*([0-9a-fA-F]{4}):\s*(.*)")

def format_hex_bytes(hex_str):
    """Formats a hex string into groups of two characters separated by a space."""
    return " ".join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)])

def extract_iperf_header_from_lines(hex_lines):
    """
    Given a list of hex dump lines (each starting with an offset),
    find the first line with offset >= 0x0020 and extract its first 16 hex digits.
    We assume the iperf header is 8 bytes:
      - The first 4 bytes: timestamp_iperf.
      - The next 4 bytes: sequencenum_iperf.
    Returns:
      timestamp_iperf_num, seq_num_num, timestamp_iperf_hex, seq_num_hex
    """
    for hl in hex_lines:
        m = hex_line_pattern.match(hl)
        if not m:
            continue
        offset_str, hex_data = m.groups()
        try:
            offset = int(offset_str, 16)
        except ValueError:
            continue
        if offset >= 0x0020:
            hex_data = hex_data.replace(" ", "")
            if len(hex_data) >= 16:
                header_hex = hex_data[:16]
                timestamp_hex = header_hex[:8]
                seq_hex = header_hex[8:16]
                try:
                    timestamp_num = int(timestamp_hex, 16)
                    seq_num = int(seq_hex, 16)
                except ValueError:
                    timestamp_num = None
                    seq_num = None
                timestamp_formatted = format_hex_bytes(timestamp_hex)
                seq_formatted = format_hex_bytes(seq_hex)
                return timestamp_num, seq_num, timestamp_formatted, seq_formatted
    return None, None, None, None

def parse_amarisoft_log(log_file, output_csv):
    last_mcs = None
    parsed_data = []
    
    with open(log_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i]
        # Update last seen MCS if line contains "mcs="
        mcs_match = mcs_line_pattern.search(line)
        if mcs_match:
            last_mcs = int(mcs_match.group(1))
            i += 1
            continue
        
        # Look for the IP line with basic info (timestamp, IP, ports)
        ip_match = ip_line_pattern.search(line)
        if ip_match:
            timestamp_log, src_ip, src_port, dst_ip, dst_port = ip_match.groups()
            # Accumulate subsequent hex dump lines into a list
            hex_lines = []
            j = i + 1
            while j < len(lines) and hex_line_pattern.match(lines[j]):
                hex_lines.append(lines[j])
                j += 1
            timestamp_iperf_num, seq_num_num, timestamp_iperf_hex, seq_num_hex = extract_iperf_header_from_lines(hex_lines)
            parsed_data.append([
                timestamp_log, src_ip, src_port, dst_ip, dst_port,
                last_mcs, timestamp_iperf_num, seq_num_num, timestamp_iperf_hex, seq_num_hex
            ])
            i = j
            continue
        
        i += 1

    # Write the extracted data to a CSV file
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "Timestamp_log", "Source IP", "Source Port", "Destination IP",
            "Destination Port", "MCS", "Timestamp_iperf", "Sequence_num_iperf",
            "Timestamp_iperf_hex", "Sequence_num_iperf_hex"
        ])
        writer.writerows(parsed_data)

# Usage of the script
log_filename = "OUTPUT/ue0.log"  # Change to your log filename


output_dir = sys.argv[1]

# Create the output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

output_filename = os.path.join(output_dir, "parsed_data.csv")
parse_amarisoft_log(log_filename, output_filename)

print(f"Data extracted and saved in {output_filename}")
