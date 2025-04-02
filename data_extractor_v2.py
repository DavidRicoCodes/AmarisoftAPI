#!/usr/bin/env python3
import re
import csv
import sys
import os
import json

if len(sys.argv) < 3:
    print("Usage: python3 data_extractor.py <output_dir> <json_file>")
    sys.exit(1)

# Get command-line parameters
output_dir = sys.argv[1]
json_file_path = sys.argv[2]

# Read the JSON and extract the id
try:
    with open(json_file_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
except Exception as e:
    print(f"Error reading JSON file: {e}")
    sys.exit(1)

id_value = "id_value_missing"
if "id" in json_data:
    id_value = json_data["id"]

# Create the output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Set output CSV filename as <ID>.csv in the provided output directory
output_csv = os.path.join(output_dir, f"{id_value}.csv")

# Set the log filename (adjust if needed)
log_filename = "/root/Desktop/OUTPUT/ue0.log"  # Change to your actual log file path if necessary

# Regular expressions for parsing
mcs_line_pattern = re.compile(r"^\s*mcs=(\d+)", re.IGNORECASE)
ip_line_pattern = re.compile(
    r"^(\d{2}:\d{2}:\d{2}\.\d{3}).*\[IP\].*? (\d+\.\d+\.\d+\.\d+):(\d+) > (\d+\.\d+\.\d+\.\d+):(\d+)"
)
hex_line_pattern = re.compile(r"^\s*([0-9a-fA-F]{4}):\s*(.*)")

def format_hex_bytes(hex_str):
    """Formats a hex string into groups of two characters separated by a space."""
    return " ".join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)])

def extract_iperf_header_from_lines(hex_lines):
    """
    Given a list of hex dump lines, find the first line with offset >= 0x0020
    and extract its first 16 hex digits.
    Assumes the iperf header is 8 bytes:
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
                # For our case, we assume:
                # bytes 0-3: timestamp_iperf (hex)
                # bytes 4-7: sequencenum_iperf (hex)
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
        # Update last seen MCS value if line contains "mcs="
        mcs_match = mcs_line_pattern.search(line)
        if mcs_match:
            last_mcs = int(mcs_match.group(1))
            i += 1
            continue
        
        # Look for an IP line with basic info (timestamp, IP, ports)
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
                last_mcs, timestamp_iperf_num, seq_num_num,
                timestamp_iperf_hex, seq_num_hex
            ])
            i = j
            continue
        
        i += 1

    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "Timestamp_log", "Source IP", "Source Port", "Destination IP",
            "Destination Port", "MCS", "Timestamp_iperf", "Sequence_num_iperf",
            "Timestamp_iperf_hex", "Sequence_num_iperf_hex"
        ])
        writer.writerows(parsed_data)

parse_amarisoft_log(log_filename, output_csv)
print(f"Data extracted and saved in {output_csv}")
