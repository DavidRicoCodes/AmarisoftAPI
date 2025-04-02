#!/usr/bin/env python3
import re
import csv
import sys
import os
import json

if len(sys.argv) < 3:
    print("Usage: python3 data_extractor_v2.py <output_dir> <json_file>")
    sys.exit(1)

# Get command-line parameters
output_dir = sys.argv[1]
json_file_path = sys.argv[2]

# Read the JSON and extract the id (if needed)
try:
    with open(json_file_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
except Exception as e:
    print(f"Error reading JSON file: {e}")
    sys.exit(1)

id_value = json_data.get("id", "id_value_missing")

# Create the output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Set output CSV filename as <ID>.csv in the provided output directory
output_csv = os.path.join(output_dir, f"{id_value}.csv")

# Set the log filename (adjust if needed)
log_filename = "/root/Desktop/OUTPUT/ue0.log"  # Change as needed

# Regular expressions for parsing
mcs_line_pattern = re.compile(r"^\s*mcs=(\d+)", re.IGNORECASE)
ip_line_pattern = re.compile(
    r"^(\d{2}:\d{2}:\d{2}\.\d{3}).*\[IP\].*? (\d+\.\d+\.\d+\.\d+):(\d+) > (\d+\.\d+\.\d+\.\d+):(\d+)"
)
hex_line_pattern = re.compile(r"^\s*([0-9a-fA-F]{4}):\s*(.*)")

def format_hex_bytes(hex_str):
    """Format a hex string into groups of two characters separated by a space."""
    return " ".join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)])

def extract_ip_id_from_line(line):
    """
    Given a hex dump line starting with "0000:", extract the IP Identification field.
    In a typical IP header, after removing spaces, the bytes are arranged as:
      Byte 0-1: Version/IHL and TOS (4 hex digits)
      Byte 2-3: Total Length (4 hex digits)
      Byte 4-5: Identification (4 hex digits)  <-- this is what we want
    So, from the concatenated hex string, extract positions 8 to 12.
    """
    m = hex_line_pattern.match(line)
    if not m:
        return "", ""
    offset_str, hex_data = m.groups()
    hex_data = hex_data.replace(" ", "")
    if len(hex_data) < 12:
        return "", ""
    ip_id_hex = hex_data[8:12]
    try:
        ip_id_dec = int(ip_id_hex, 16)
    except ValueError:
        ip_id_dec = ""
    return format_hex_bytes(ip_id_hex), ip_id_dec

def extract_ip_checksum_from_line(line):
    """
    Given a hex dump line starting with "0000:", extract the IP header checksum.
    In a typical IP header, the checksum is at bytes 10-11 (positions 20-24 in the hex string).
    """
    m = hex_line_pattern.match(line)
    if not m:
        return "", ""
    offset_str, hex_data = m.groups()
    hex_data = hex_data.replace(" ", "")
    if len(hex_data) < 24:
        return "", ""
    ip_checksum_hex = hex_data[20:24]
    try:
        ip_checksum_dec = int(ip_checksum_hex, 16)
    except ValueError:
        ip_checksum_dec = ""
    return format_hex_bytes(ip_checksum_hex), ip_checksum_dec

def extract_udp_checksum_from_line(line):
    """
    Given a hex dump line starting with "0010:", extract the UDP header checksum.
    For our sample line:
      0010:  0a 03 07 0b d2 26 04 03  05 b0 18 e5 00 92 10 30
    As the IP header is complete in "0000:" line, we consider the "0010:" line to hold:
      - The first 4 bytes complete the remainder of IP header (not used here)
      - The next 8 bytes form the UDP header.
    In the UDP header, the checksum is at bytes 6-7, i.e. positions 12 to 16 of the UDP header data.
    Since here the UDP header data starts at position 8 of the line's hex data, we extract from
    position 8+4 = 12 to 8+8 = 16.
    """
    m = hex_line_pattern.match(line)
    if not m:
        return "", ""
    offset_str, hex_data = m.groups()
    hex_data = hex_data.replace(" ", "")
    if len(hex_data) < 24:
        return "", ""
    # UDP header is assumed to be in positions 8 to 24 of this line's hex data.
    udp_header = hex_data[8:24]
    # UDP checksum is bytes 6-7 of the UDP header → positions 12 to 16 of udp_header.
    udp_checksum_hex = udp_header[12:16]
    try:
        udp_checksum_dec = int(udp_checksum_hex, 16)
    except ValueError:
        udp_checksum_dec = ""
    return format_hex_bytes(udp_checksum_hex), udp_checksum_dec

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

        # Look for an IP line with basic info (timestamp, IP, ports)
        ip_match = ip_line_pattern.search(line)
        if ip_match:
            timestamp_log, src_ip, src_port, dst_ip, dst_port = ip_match.groups()
            # Identify hex dump lines for IP and UDP headers
            hex_line_0000 = None
            hex_line_0010 = None
            j = i + 1
            while j < len(lines) and hex_line_pattern.match(lines[j]):
                m_line = hex_line_pattern.match(lines[j])
                if m_line:
                    offset_str, _ = m_line.groups()
                    try:
                        offset = int(offset_str, 16)
                    except ValueError:
                        offset = -1
                    if offset == 0x0000:
                        hex_line_0000 = lines[j]
                    elif offset == 0x0010:
                        hex_line_0010 = lines[j]
                j += 1

            # Extract IP Identification and IP Checksum from hex_line_0000
            ip_id_hex, ip_id_dec = ("", "")
            ip_checksum_hex, ip_checksum_dec = ("", "")
            if hex_line_0000:
                ip_id_hex, ip_id_dec = extract_ip_id_from_line(hex_line_0000)
                ip_checksum_hex, ip_checksum_dec = extract_ip_checksum_from_line(hex_line_0000)
            
            # Extract UDP checksum from hex_line_0010
            udp_checksum_hex, udp_checksum_dec = ("", "")
            if hex_line_0010:
                udp_checksum_hex, udp_checksum_dec = extract_udp_checksum_from_line(hex_line_0010)
            
            # Accumulate all hex dump lines that follow (for iperf header extraction)
            hex_lines = []
            k = i + 1
            while k < len(lines) and hex_line_pattern.match(lines[k]):
                hex_lines.append(lines[k])
                k += 1
            timestamp_iperf_num, seq_num_num, timestamp_iperf_hex, seq_num_hex = extract_iperf_header_from_lines(hex_lines)
            
            # Order the columns: primero datos IP, luego UDP, luego payload
            parsed_data.append([
                timestamp_log,       # Timestamp_log
                src_ip,              # Source IP
                dst_ip,              # Destination IP
                ip_id_hex,           # IP Identification (hex)
                ip_id_dec,           # IP Identification (dec)
                ip_checksum_hex,     # IP Checksum (hex)
                ip_checksum_dec,     # IP Checksum (dec)
                src_port,            # Source Port
                dst_port,            # Destination Port
                udp_checksum_hex,    # UDP Checksum (hex)
                udp_checksum_dec,    # UDP Checksum (dec)
                last_mcs,            # MCS
                timestamp_iperf_num, # Timestamp_iperf (numeric)
                timestamp_iperf_hex, # Timestamp_iperf (hex)
                seq_num_num,         # Sequence_num_iperf (numeric)
                seq_num_hex          # Sequence_num_iperf (hex)
            ])
            i = k
            continue
        
        i += 1

    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "Timestamp_log", "Source IP", "Destination IP", 
            "IP_ID_hex", "IP_ID_dec", "IP_Checksum_hex", "IP_Checksum_dec",
            "Source Port", "Destination Port", "UDP_Checksum_hex", "UDP_Checksum_dec",
            "MCS", "Timestamp_iperf", "Timestamp_iperf_hex", "Sequence_num_iperf", "Sequence_num_iperf_hex"
        ])
        writer.writerows(parsed_data)

parse_amarisoft_log(log_filename, output_csv)
print(f"Data extracted and saved in {output_csv}")
